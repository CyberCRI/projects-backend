import json
import uuid

from django.conf import settings
from django.db import transaction
from django.db.models import Case, Prefetch, Q, QuerySet, Value, When
from django.db.utils import IntegrityError
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiTypes,
    extend_schema,
    inline_serializer,
)
from googleapiclient.errors import HttpError
from rest_framework import mixins, status, views, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.serializers import BooleanField
from rest_framework.views import APIView

from apps.accounts.filters import PeopleGroupFilter, SkillFilter
from apps.accounts.utils import get_permission_from_representation
from apps.commons.permissions import IsOwner, WillBeOwner
from apps.commons.utils.permissions import map_action_to_permission
from apps.files.models import Image
from apps.files.views import ImageStorageView
from apps.organizations.models import Organization, ProjectCategory
from apps.organizations.permissions import HasOrganizationPermission
from apps.organizations.utils import get_hierarchy_codes
from apps.projects.serializers import ProjectLightSerializer
from keycloak import KeycloakDeleteError, KeycloakPostError, KeycloakPutError
from services.google.utils import (
    suspend_google_account,
    update_or_create_google_account,
    update_or_create_google_group,
)
from services.keycloak.interface import KeycloakService

from .models import AnonymousUser, PeopleGroup, PrivacySettings, ProjectUser, Skill
from .permissions import HasBasePermission, HasPeopleGroupPermission, ReadOnly
from .serializers import (
    AccessTokenSerializer,
    CredentialsSerializer,
    EmptyPayloadResponseSerializer,
    PeopleGroupAddFeaturedProjectsSerializer,
    PeopleGroupAddTeamMembersSerializer,
    PeopleGroupLightSerializer,
    PeopleGroupRemoveFeaturedProjectsSerializer,
    PeopleGroupRemoveTeamMembersSerializer,
    PeopleGroupSerializer,
    PrivacySettingsSerializer,
    SkillSerializer,
    UserLightSerializer,
    UserSerializer,
)


class RetrieveUpdateModelViewSet(
    mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet
):
    """
    A viewset that provides `retrieve`, `list`, `update` and `partial_update`
    actions.

    To use it, override the class and set the `.queryset` and
    `.serializer_class` attributes.
    """


class ReadUpdateModelViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    A viewset that provides `retrieve`, `list`, `update` and `partial_update`
    actions.

    To use it, override the class and set the `.queryset` and
    `.serializer_class` attributes.
    """


class UserViewSet(viewsets.ModelViewSet):
    serializer_class = UserSerializer
    lookup_field = "keycloak_id"
    lookup_value_regex = "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
    search_fields = [
        "given_name",
        "family_name",
        "email",
        "job",
        "groups__people_groups__name",
    ]
    filter_backends = (DjangoFilterBackend, OrderingFilter, SearchFilter)
    ordering_fields = ["given_name", "family_name", "job", "current_org_role"]

    def get_permissions(self):
        codename = map_action_to_permission(self.action, "projectuser")
        if codename:
            self.permission_classes = [
                IsAuthenticatedOrReadOnly,
                ReadOnly
                | IsOwner
                | HasBasePermission(codename, "accounts")
                | HasOrganizationPermission(codename),
            ]
        return super().get_permissions()

    def get_queryset(self):
        queryset = self.request.user.get_user_queryset()
        organization_pk = self.request.query_params.get("current_org_pk", None)
        if organization_pk is not None:
            organization = Organization.objects.get(pk=organization_pk)
            return queryset.annotate(
                current_org_role=Case(
                    When(
                        pk__in=organization.admins.values_list("pk", flat=True),
                        then=Value(Organization.DefaultGroup.ADMINS),
                    ),
                    When(
                        pk__in=organization.facilitators.values_list("pk", flat=True),
                        then=Value(Organization.DefaultGroup.FACILITATORS),
                    ),
                    When(
                        pk__in=organization.users.values_list("pk", flat=True),
                        then=Value(Organization.DefaultGroup.USERS),
                    ),
                    default=Value(None),
                )
            )
        return queryset

    def get_object(self):
        try:
            return super().get_object()
        except Http404:
            lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
            if not ProjectUser.objects.filter(
                **{self.lookup_field: self.kwargs[lookup_url_kwarg]}
            ).exists():
                return KeycloakService.import_user(self.kwargs[self.lookup_field])
            raise Http404()

    def get_serializer_class(self):
        if self.action in ["list"]:
            return UserLightSerializer
        return self.serializer_class

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="current_org_pk",
                description="Organization id used to fetch the role of the users in the organization",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="current_org_role",
                description="Used to filter the users by role in the organization",
                required=False,
                type=str,
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        responses={200: UserSerializer},
    )
    @action(detail=False, methods=["GET"])
    def anonymous(self, request, *args, **kwargs):
        user = AnonymousUser()
        return Response(user.serialize(), status=status.HTTP_200_OK)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="permissions",
                description="Representations of the permissions to check, separated by a comma",
                required=False,
                type=str,
            )
        ],
        responses={
            200: inline_serializer(name="Result", fields={"result": BooleanField()})
        },
    )
    @action(detail=True, methods=["GET"])
    def has_permissions(self, request, *args, **kwargs):
        user = self.get_object()
        permissions = self.request.query_params.get("permissions", "").split(",")
        for permission in permissions:
            codename, instance = get_permission_from_representation(permission)
            if not codename:
                raise Http404("Permission not found")
            if instance and user.has_perm(codename, instance):
                return Response({"result": True}, status=status.HTTP_200_OK)
            if not instance and user.has_perm(codename):
                return Response({"result": True}, status=status.HTTP_200_OK)
        return Response({"result": False}, status=status.HTTP_200_OK)

    def google_sync(self, instance, data, created):
        create_in_google = data.get("create_in_google", False)
        main_google_group = data.get(
            "main_google_group", "Admin Staff" if created else ""
        )
        notify = not created
        update_or_create_google_account(
            instance, create_in_google, main_google_group, notify
        )
        instance.refresh_from_db()

    def create(self, request, *args, **kwargs):
        try:
            data = request.data.copy()
            data["keycloak_id"] = KeycloakService.create_user(data)
            serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception=True)
            instance = self.perform_create(serializer)
            self.google_sync(instance, self.request.data, True)
            headers = self.get_success_headers(serializer.data)
            return Response(
                serializer.data, status=status.HTTP_201_CREATED, headers=headers
            )
        except (KeycloakPostError, KeycloakPutError) as e:
            keycloak_error = json.loads(e.response_body.decode()).get("errorMessage")
            return Response(
                {"error": f"An error occured in Keycloak : {keycloak_error}"},
                status=e.response_code,
            )
        except HttpError as e:
            return Response(
                {
                    "error": f"User was created but an error occured in Google : {e.reason}"
                },
                status=e.status_code,
            )

    def perform_create(self, serializer):
        if hasattr(self.request.user, "invitation"):
            invitation = self.request.user.invitation
            groups = [
                invitation.people_group.get_members()
                if invitation.people_group
                else None,
                invitation.organization.get_users()
                if invitation.organization
                else None,
            ]
            return serializer.save(groups=list(filter(lambda x: x, groups)))
        return serializer.save()

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            suspend_google_account(instance)
            with transaction.atomic():
                response = super().destroy(request, *args, **kwargs)
                KeycloakService.delete_user(instance)
            return response
        except KeycloakDeleteError as e:
            keycloak_error = json.loads(e.response_body.decode()).get("errorMessage")
            return Response(
                {"error": f"An error occured in Keycloak : {keycloak_error}"},
                status=e.response_code,
            )
        except HttpError as e:
            google_error = e.reason
            return Response(
                {"error": f"An error occured in Google : {google_error}"},
                status=e.status_code,
            )

    def update(self, request, *args, **kwargs):
        try:
            return super().update(request, *args, **kwargs)
        except KeycloakPutError as e:
            keycloak_error = json.loads(e.response_body.decode()).get("errorMessage")
            return Response(
                {"error": f"An error occured in Keycloak : {keycloak_error}"},
                status=e.response_code,
            )
        except HttpError as e:
            return Response(
                {
                    "error": f"User was updated but an error occured in Google : {e.reason}"
                },
                status=e.status_code,
            )

    def perform_update(self, serializer):
        with transaction.atomic():
            instance = serializer.save()
            KeycloakService.update_user(instance)
        self.google_sync(instance, self.request.data, False)

    @extend_schema(responses={204: OpenApiTypes.NONE})
    @action(
        detail=True,
        methods=["GET"],
        url_path="reset-password",
        permission_classes=[
            IsAuthenticated,
            IsOwner
            | HasBasePermission("change_projectuser", "accounts")
            | HasOrganizationPermission("change_projectuser"),
        ],
    )
    def reset_password(self, request, *args, **kwargs):
        user = self.get_object()
        KeycloakService.send_reset_password_email(user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class PeopleGroupViewSet(viewsets.ModelViewSet):
    queryset = PeopleGroup.objects.all()
    serializer_class = PeopleGroupSerializer
    filterset_class = PeopleGroupFilter
    lookup_field = "id"

    def get_permissions(self):
        codename = map_action_to_permission(self.action, "peoplegroup")
        if codename:
            self.permission_classes = [
                IsAuthenticatedOrReadOnly,
                ReadOnly
                | HasBasePermission(codename, "accounts")
                | HasOrganizationPermission(codename)
                | HasPeopleGroupPermission(codename),
            ]
        return super().get_permissions()

    def get_queryset(self) -> QuerySet:
        """Prefetch related models"""
        if "organization_code" in self.kwargs:
            organization = Prefetch(
                "organization",
                queryset=Organization.objects.select_related(
                    "faq", "parent", "banner_image", "logo_image"
                ).prefetch_related("wikipedia_tags"),
            )
            return self.request.user.get_people_group_queryset(organization).filter(
                organization__code__in=get_hierarchy_codes(
                    [self.kwargs["organization_code"]]
                )
            )
        return PeopleGroup.objects.none()

    def get_serializer_class(self):
        if self.action == "list":
            return PeopleGroupLightSerializer
        return self.serializer_class

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context

    def google_sync(self, instance, data):
        create_in_google = data.get("create_in_google", False)
        update_or_create_google_group(instance, create_in_google)
        instance.refresh_from_db()

    def create(self, request, *args, **kwargs):
        try:
            organization = get_object_or_404(
                Organization, code=self.kwargs["organization_code"]
            )
            request.data.update({"organization": organization.code})
            return super().create(request, *args, **kwargs)
        except HttpError as e:
            return Response(
                {"error": f"An error occured in Google : {e.reason}"},
                status=e.status_code,
            )

    @transaction.atomic
    def perform_create(self, serializer):
        people_group = serializer.save()
        people_group.setup_permissions(self.request.user)
        self.google_sync(people_group, self.request.data)

    def update(self, request, *args, **kwargs):
        try:
            return super().update(request, *args, **kwargs)
        except HttpError as e:
            return Response(
                {"error": f"An error occured in Google : {e.reason}"},
                status=e.status_code,
            )

    @transaction.atomic
    def perform_update(self, serializer):
        instance = serializer.save()
        self.google_sync(instance, self.request.data)

    @extend_schema(
        request=PeopleGroupAddTeamMembersSerializer, responses=PeopleGroupSerializer
    )
    @action(
        detail=True,
        methods=["POST"],
        url_path="member/add",
        permission_classes=[
            IsAuthenticated,
            HasBasePermission("change_peoplegroup", "accounts")
            | HasOrganizationPermission("change_peoplegroup")
            | HasPeopleGroupPermission("change_peoplegroup"),
        ],
    )
    def add_member(self, request, *args, **kwargs):
        try:
            people_group = self.get_object()
            serializer = PeopleGroupAddTeamMembersSerializer(
                data={"people_group": people_group.pk, **request.data}
            )
            serializer.is_valid(raise_exception=True)
            with transaction.atomic():
                serializer.save()
                self.google_sync(people_group, dict())
            return Response(status=status.HTTP_204_NO_CONTENT)
        except HttpError as e:
            return Response(
                {"error": f"An error occured in Google : {e.reason}"},
                status=e.status_code,
            )

    @extend_schema(
        request=PeopleGroupRemoveTeamMembersSerializer, responses=PeopleGroupSerializer
    )
    @action(
        detail=True,
        methods=["POST"],
        url_path="member/remove",
        permission_classes=[
            IsAuthenticated,
            HasBasePermission("change_peoplegroup", "accounts")
            | HasOrganizationPermission("change_peoplegroup")
            | HasPeopleGroupPermission("change_peoplegroup"),
        ],
    )
    def remove_member(self, request, *args, **kwargs):
        try:
            people_group = self.get_object()
            serializer = PeopleGroupRemoveTeamMembersSerializer(
                data={"people_group": people_group.pk, **request.data}
            )
            serializer.is_valid(raise_exception=True)
            with transaction.atomic():
                serializer.save()
                self.google_sync(people_group, dict())
            return Response(status=status.HTTP_204_NO_CONTENT)
        except HttpError as e:
            return Response(
                {"error": f"An error occured in Google : {e.reason}"},
                status=e.status_code,
            )

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="limit",
                description="Number of results to return per page.",
                required=False,
                type=int,
            ),
            OpenApiParameter(
                name="offset",
                description="The initial index from which to return the results.",
                required=False,
                type=int,
            ),
        ]
    )
    @action(
        detail=True,
        methods=["GET"],
        url_path="member",
        permission_classes=[ReadOnly],
    )
    def member(self, request, *args, **kwargs):
        group = self.get_object()
        managers_ids = group.managers.all().values_list("keycloak_id", flat=True)
        leaders_ids = group.leaders.all().values_list("keycloak_id", flat=True)
        queryset = (
            group.get_all_members()
            .distinct()
            .annotate(
                is_leader=Case(
                    When(keycloak_id__in=leaders_ids, then=True), default=Value(False)
                )
            )
            .annotate(
                is_manager=Case(
                    When(keycloak_id__in=managers_ids, then=True), default=Value(False)
                )
            )
            .order_by("-is_leader", "-is_manager")
        )

        page = self.paginate_queryset(queryset)
        if page is not None:
            user_serializer = UserLightSerializer(
                page, many=True, context={"request": request}
            )
            return self.get_paginated_response(user_serializer.data)

        user_serializer = UserLightSerializer(
            queryset, many=True, context={"request": request}
        )
        return Response(user_serializer.data)

    @extend_schema(
        request=PeopleGroupAddFeaturedProjectsSerializer,
        responses=PeopleGroupSerializer,
    )
    @action(
        detail=True,
        methods=["POST"],
        url_path="project/add",
        permission_classes=[
            IsAuthenticated,
            HasBasePermission("change_peoplegroup", "accounts")
            | HasOrganizationPermission("change_peoplegroup")
            | HasPeopleGroupPermission("change_peoplegroup"),
        ],
    )
    @transaction.atomic
    def add_featured_project(self, request, *args, **kwargs):
        people_group = self.get_object()
        serializer = PeopleGroupAddFeaturedProjectsSerializer(
            data={"people_group": people_group.pk, **request.data},
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        request=PeopleGroupRemoveFeaturedProjectsSerializer,
        responses=PeopleGroupSerializer,
    )
    @action(
        detail=True,
        methods=["POST"],
        url_path="project/remove",
        permission_classes=[
            IsAuthenticated,
            HasBasePermission("change_peoplegroup", "accounts")
            | HasOrganizationPermission("change_peoplegroup")
            | HasPeopleGroupPermission("change_peoplegroup"),
        ],
    )
    def remove_featured_project(self, request, *args, **kwargs):
        people_group = self.get_object()
        serializer = PeopleGroupRemoveFeaturedProjectsSerializer(
            data={"people_group": people_group.pk, **request.data}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="limit",
                description="Number of results to return per page.",
                required=False,
                type=int,
            ),
            OpenApiParameter(
                name="offset",
                description="The initial index from which to return the results.",
                required=False,
                type=int,
            ),
        ]
    )
    @action(
        detail=True,
        methods=["GET"],
        url_path="project",
        permission_classes=[ReadOnly],
    )
    def project(self, request, *args, **kwargs):
        group = self.get_object()
        categories = Prefetch(
            "categories",
            queryset=ProjectCategory.objects.select_related("organization"),
        )
        featured_projects_ids = [p.id for p in group.featured_projects.all()]
        queryset = (
            self.request.user.get_project_queryset()
            .filter(
                Q(id__in=featured_projects_ids)
                | Q(groups__users__in=group.get_all_members().all())
            )
            .distinct()
            .prefetch_related(categories)
            .annotate(
                is_featured=Case(
                    When(id__in=featured_projects_ids, then=True), default=Value(False)
                )
            )
            .order_by("-is_featured")
        )

        page = self.paginate_queryset(queryset)
        if page is not None:
            project_serializer = ProjectLightSerializer(
                page, context={"request": request}, many=True
            )
            return self.get_paginated_response(project_serializer.data)

        project_serializer = ProjectLightSerializer(
            queryset, context={"request": request}, many=True
        )
        return Response(project_serializer.data)

    @action(
        detail=True,
        methods=["GET"],
        url_path="hierarchy",
        permission_classes=[ReadOnly],
    )
    def hierarchy(self, request, *args, **kwargs):
        people_group = self.get_object()
        if people_group.type != "group":
            return Response(
                {
                    "error": "Hierarchy is only available for 'group' type people-groups."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(people_group.get_hierarchy(), status=status.HTTP_200_OK)


class PeopleGroupHeaderView(ImageStorageView):
    permission_classes = [
        IsAuthenticatedOrReadOnly,
        ReadOnly
        | IsOwner
        | HasBasePermission("change_peoplegroup", "accounts")
        | HasOrganizationPermission("change_peoplegroup")
        | HasPeopleGroupPermission("change_peoplegroup"),
    ]
    lookup_field = "id"
    lookup_value_regex = "[0-9]+"

    def get_object(self):
        """
        Retrieve the object within the QuerySet.
        There should be only one Image in the QuerySet.
        """
        queryset = self.filter_queryset(self.get_queryset())
        obj = get_object_or_404(queryset)
        self.check_object_permissions(self.request, obj)
        return obj

    def get_queryset(self):
        if all(k in self.kwargs for k in ["people_group_id", "organization_code"]):
            people_group = PeopleGroup.objects.get(
                organization__code=self.kwargs["organization_code"],
                id=self.kwargs["people_group_id"],
            )
            return Image.objects.filter(people_group_header=people_group)
        return Image.objects.none

    @staticmethod
    def upload_to(instance, filename) -> str:
        return f"people_group/header/{uuid.uuid4()}#{instance.name}"

    def add_image_to_model(self, image):
        if "people_group_id" in self.kwargs:
            people_group = PeopleGroup.objects.get(id=self.kwargs["people_group_id"])
            people_group.header_image = image
            people_group.save()
            return f"/v1/people-group/{self.kwargs['people_group_id']}/header"
        return None


class PeopleGroupLogoView(ImageStorageView):
    permission_classes = [
        IsAuthenticatedOrReadOnly,
        ReadOnly
        | IsOwner
        | HasBasePermission("change_peoplegroup", "accounts")
        | HasOrganizationPermission("change_peoplegroup")
        | HasPeopleGroupPermission("change_peoplegroup"),
    ]
    lookup_field = "id"
    lookup_value_regex = "[0-9]+"

    def get_object(self):
        """
        Retrieve the object within the QuerySet.
        There should be only one Image in the QuerySet.
        """
        queryset = self.filter_queryset(self.get_queryset())
        obj = get_object_or_404(queryset)
        self.check_object_permissions(self.request, obj)
        return obj

    def get_queryset(self):
        if all(k in self.kwargs for k in ["people_group_id", "organization_code"]):
            people_group = PeopleGroup.objects.get(
                organization__code=self.kwargs["organization_code"],
                id=self.kwargs["people_group_id"],
            )
            return Image.objects.filter(people_group_logo=people_group)
        return Image.objects.none

    @staticmethod
    def upload_to(instance, filename) -> str:
        return f"people_group/logo/{uuid.uuid4()}#{instance.name}"

    def add_image_to_model(self, image):
        if "people_group_id" in self.kwargs:
            people_group = PeopleGroup.objects.get(id=self.kwargs["people_group_id"])
            people_group.logo_image = image
            people_group.save()
            return f"/v1/people_group/{self.kwargs['people_group_id']}/logo"
        return None


class SkillViewSet(viewsets.ModelViewSet):
    queryset = Skill.objects.all()
    serializer_class = SkillSerializer
    filterset_class = SkillFilter
    permission_classes = [
        IsAuthenticatedOrReadOnly,
        ReadOnly
        | IsOwner
        | WillBeOwner
        | HasBasePermission("change_projectuser", "accounts")
        | HasOrganizationPermission("change_projectuser"),
    ]

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except IntegrityError:
            return Response(
                {"error": "Skill already added"}, status=status.HTTP_409_CONFLICT
            )


class DeleteCookieView(views.APIView):
    @extend_schema(request=None, responses=EmptyPayloadResponseSerializer)
    def get(self, request, *args, **kwargs):
        access_token = request.COOKIES.get(settings.JWT_ACCESS_TOKEN_COOKIE_NAME, None)
        if not access_token:
            return HttpResponse("Cookie already deleted")
        response = HttpResponse("Cookie deleted")
        response.delete_cookie(settings.JWT_ACCESS_TOKEN_COOKIE_NAME, samesite="None")
        return response


class UserProfilePictureView(ImageStorageView):
    permission_classes = [
        IsAuthenticatedOrReadOnly,
        ReadOnly
        | IsOwner
        | WillBeOwner
        | HasBasePermission("change_projectuser", "accounts")
        | HasOrganizationPermission("change_projectuser"),
    ]

    def get_queryset(self):
        if "user_keycloak_id" in self.kwargs:
            user = ProjectUser.objects.get(keycloak_id=self.kwargs["user_keycloak_id"])
            if self.request.user.is_anonymous:
                return Image.objects.filter(user=user)
            return Image.objects.filter(
                Q(user=user) | Q(owner=self.request.user)
            ).distinct()
        return Image.objects.none

    @staticmethod
    def upload_to(instance, filename) -> str:
        return f"account/profile/{uuid.uuid4()}#{instance.name}"

    def add_image_to_model(self, image):
        if "user_keycloak_id" in self.kwargs:
            user = ProjectUser.objects.get(keycloak_id=self.kwargs["user_keycloak_id"])
            user.profile_picture = image
            user.save()
            image.owner = user
            image.save()
            return (
                f"/v1/user/{self.kwargs['user_keycloak_id']}/profile-picture/{image.id}"
            )
        return None


class PrivacySettingsViewSet(RetrieveUpdateModelViewSet):
    """Allows getting or modifying a user's privacy settings."""

    permission_classes = [
        IsAuthenticatedOrReadOnly,
        ReadOnly
        | IsOwner
        | HasBasePermission("change_projectuser", "accounts")
        | HasOrganizationPermission("change_projectuser"),
    ]
    serializer_class = PrivacySettingsSerializer
    lookup_field = "user_id"
    lookup_url_kwarg = "user_keycloak_id"

    def get_queryset(self):
        qs = self.request.user.get_user_related_queryset(PrivacySettings.objects.all())
        if "user_keycloak_id" in self.kwargs:
            return qs.filter(user__keycloak_id=self.kwargs["user_keycloak_id"])
        return qs


class AccessTokenView(APIView):
    @extend_schema(request=CredentialsSerializer, responses=AccessTokenSerializer)
    def post(self, request):
        serializer = CredentialsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        code, token = KeycloakService.get_token_for_user(
            request.data["username"], request.data["password"]
        )
        return Response(AccessTokenSerializer(token).data, status=code)
