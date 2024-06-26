import uuid

from django.conf import settings
from django.db import transaction
from django.db.models import Case, Prefetch, Q, QuerySet, Value, When
from django.db.utils import IntegrityError
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils import translation
from django.utils.decorators import method_decorator
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiTypes,
    extend_schema,
    inline_serializer,
)
from googleapiclient.errors import HttpError
from rest_framework import status, views, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.parsers import JSONParser
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework.serializers import BooleanField
from rest_framework.views import APIView

from apps.commons.filters import TrigramSearchFilter
from apps.commons.permissions import IsOwner, ReadOnly, WillBeOwner
from apps.commons.serializers import EmailAddressSerializer
from apps.commons.utils import map_action_to_permission
from apps.commons.views import (
    DetailOnlyViewset,
    MultipleIDViewset,
    OrganizationRelatedViewset,
    PeopleGroupRelatedViewSet,
    RetrieveUpdateModelViewSet,
    UserRelatedViewSet,
)
from apps.files.models import Image
from apps.files.views import ImageStorageView
from apps.organizations.models import Organization, ProjectCategory
from apps.organizations.permissions import HasOrganizationPermission
from apps.projects.models import Project
from apps.projects.serializers import ProjectLightSerializer
from keycloak import (
    KeycloakDeleteError,
    KeycloakGetError,
    KeycloakPostError,
    KeycloakPutError,
)
from services.google.models import GoogleAccount, GoogleGroup
from services.google.tasks import (
    create_google_account,
    create_google_group,
    suspend_google_account,
    update_google_account,
    update_google_group,
)
from services.keycloak.exceptions import KeycloakAccountNotFound
from services.keycloak.interface import KeycloakService

from .exceptions import (
    EmailTypeMissingError,
    PermissionNotFoundError,
    SkillAlreadyAddedError,
)
from .filters import PeopleGroupFilter, SkillFilter, UserFilter
from .models import AnonymousUser, PeopleGroup, PrivacySettings, ProjectUser, Skill
from .parsers import UserMultipartParser
from .permissions import HasBasePermission, HasPeopleGroupPermission
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
    UserAdminListSerializer,
    UserLightSerializer,
    UserSerializer,
)
from .utils import (
    account_sync_errors_handler,
    get_default_group,
    get_permission_from_representation,
)


class UserViewSet(MultipleIDViewset, OrganizationRelatedViewset, viewsets.ModelViewSet):
    serializer_class = UserSerializer
    lookup_field = "id"
    lookup_value_regex = (
        "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|[a-zA-Z0-9-]{1,}"
    )
    search_fields = [
        "given_name",
        "family_name",
        "email",
        "job",
    ]
    parser_classes = (JSONParser, UserMultipartParser)
    filter_backends = (
        TrigramSearchFilter,
        DjangoFilterBackend,
        OrderingFilter,
    )
    filterset_class = UserFilter
    ordering_fields = [
        "given_name",
        "family_name",
        "job",
        "current_org_role",
        "email_verified",
        "password_created",
        "last_login",
        "created_at",
    ]
    multiple_lookup_fields = [
        (ProjectUser, "id"),
    ]

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

    def annotate_organization_role(
        self, queryset: QuerySet, organization: Organization
    ) -> QuerySet:
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

    def annotate_keycloak_email_verified(self, queryset: QuerySet) -> QuerySet:
        email_not_verified = KeycloakService.get_users(emailVerified=False)
        email_not_verified = [user["id"] for user in email_not_verified]
        return queryset.annotate(
            email_verified=Case(
                When(
                    keycloak_account__isnull=True,
                    then=Value(False),
                ),
                When(
                    keycloak_account__keycloak_id__in=email_not_verified,
                    then=Value(False),
                ),
                default=Value(True),
            )
        )

    def get_queryset(self):
        queryset = self.request.user.get_user_queryset()
        queryset = self.annotate_organization_role(queryset, self.organization)
        if self.action == "admin_list":
            queryset = self.annotate_keycloak_email_verified(queryset)
        return queryset.prefetch_related(
            "skills__wikipedia_tag",
            "groups",
        )

    def get_serializer_class(self):
        if self.action == "list":
            return UserLightSerializer
        if self.action == "admin_list":
            return UserAdminListSerializer
        return self.serializer_class

    @action(
        detail=False,
        methods=["GET"],
        url_path="get-by-email/(?P<email>[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+.[a-zA-Z0-9-.]+)",
        url_name="get-by-email",
        permission_classes=[HasBasePermission("get_user_by_email", "accounts")],
    )
    def get_by_email(self, request, *args, **kwargs):
        queryset = ProjectUser.objects.all()
        queryset = self.annotate_organization_role(queryset, self.organization)
        user = queryset.filter(
            Q(email=kwargs.get("email")) | Q(personal_email=kwargs.get("email"))
        ).distinct()
        if user.exists():
            context = {
                **self.get_serializer_context(),
                "force_display": True,
            }
            return Response(UserLightSerializer(user.get(), context=context).data)
        raise Http404

    @extend_schema(
        parameters=[
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
        parameters=[
            OpenApiParameter(
                name="current_org_role",
                description="Used to filter the users by role in the organization",
                required=False,
                type=str,
            ),
        ]
    )
    @action(
        detail=False,
        methods=["GET"],
        url_path="admin-list",
        url_name="admin-list",
        permission_classes=[IsAuthenticated],
    )
    def admin_list(self, request, *args, **kwargs):
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
                raise PermissionNotFoundError
            if instance and user.has_perm(codename, instance):
                return Response({"result": True}, status=status.HTTP_200_OK)
            if not instance and user.has_perm(codename):
                return Response({"result": True}, status=status.HTTP_200_OK)
        return Response({"result": False}, status=status.HTTP_200_OK)

    def google_sync(self, instance, data, created):
        create_in_google = data.get("create_in_google", False)
        organizational_unit = data.get(
            "google_organizational_unit",
            settings.GOOGLE_DEFAULT_ORG_UNIT if created else None,
        )
        exists_in_google = GoogleAccount.objects.filter(user=instance).exists()
        if create_in_google and not exists_in_google:
            create_google_account(instance, organizational_unit)
        elif not create_in_google and exists_in_google:
            update_google_account(instance, organizational_unit)
        instance.refresh_from_db()
        return instance

    @method_decorator(
        account_sync_errors_handler(
            keycloak_error=(KeycloakPostError, KeycloakPutError, KeycloakGetError)
        )
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        with transaction.atomic():
            if hasattr(self.request.user, "invitation"):
                invitation = self.request.user.invitation
                groups = [
                    get_default_group(),
                    (
                        invitation.people_group.get_members()
                        if invitation.people_group
                        else None
                    ),
                    (
                        invitation.organization.get_users()
                        if invitation.organization
                        else None
                    ),
                ]
                instance = serializer.save(groups=list(filter(lambda x: x, groups)))
                email_type = KeycloakService.EmailType.INVITATION
                redirect_organization_code = invitation.organization.code
            else:
                instance = serializer.save()
                email_type = KeycloakService.EmailType.ADMIN_CREATED
                redirect_organization_code = self.organization.code

            instance = self.google_sync(instance, self.request.data, True)
            keycloak_account = KeycloakService.create_user(
                instance, self.request.data.get("password", None)
            )
        KeycloakService.send_email(
            keycloak_account=keycloak_account,
            email_type=email_type,
            redirect_organization_code=redirect_organization_code,
        )
        return instance

    @method_decorator(account_sync_errors_handler(keycloak_error=KeycloakDeleteError))
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @transaction.atomic
    def perform_destroy(self, instance):
        suspend_google_account(instance)
        if hasattr(instance, "keycloak_account"):
            KeycloakService.delete_user(instance.keycloak_account)
        instance.delete()

    @method_decorator(account_sync_errors_handler(keycloak_error=KeycloakPutError))
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @transaction.atomic
    def perform_update(self, serializer):
        instance = serializer.save()
        if hasattr(instance, "keycloak_account"):
            KeycloakService.update_user(instance.keycloak_account)
        self.google_sync(instance, self.request.data, False)

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
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
    def force_reset_password(self, request, *args, **kwargs):
        user = self.get_object()
        if hasattr(user, "keycloak_account"):
            KeycloakService.send_email(
                keycloak_account=user.keycloak_account,
                email_type=KeycloakService.EmailType.FORCE_RESET_PASSWORD,
                actions=["UPDATE_PASSWORD"],
                redirect_organization_code=self.organization.code,
            )
            return Response({"detail": "Email sent"}, status=status.HTTP_200_OK)
        raise KeycloakAccountNotFound

    @extend_schema(request=EmailAddressSerializer, responses={200: OpenApiTypes.OBJECT})
    @action(
        detail=False,
        methods=["POST"],
        url_path="reset-password",
        permission_classes=[],
    )
    def reset_password(self, request, *args, **kwargs):
        serializer = EmailAddressSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        user = ProjectUser.objects.filter(email=email)
        if not user.exists():
            user = get_object_or_404(ProjectUser, personal_email=email)
        else:
            user = user.get()
        redirect_uri = request.query_params.get("redirect_uri", "")
        if hasattr(user, "keycloak_account"):
            KeycloakService.send_reset_password_email(
                user=user.keycloak_account, redirect_uri=redirect_uri
            )
            return Response({"detail": "Email sent"}, status=status.HTTP_200_OK)
        raise KeycloakAccountNotFound

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    @action(
        detail=True,
        methods=["GET"],
        url_path="refresh-keycloak-actions-link",
        permission_classes=[ReadOnly],
    )
    def refresh_keycloak_actions_link(self, request, *args, **kwargs):
        user = self.get_object()
        try:
            email_type = request.query_params.get("email_type", None)
            if not email_type:
                raise EmailTypeMissingError
            if not hasattr(user, "keycloak_account"):
                raise KeycloakAccountNotFound
            email_sent = KeycloakService.send_email(
                keycloak_account=user.keycloak_account,
                email_type=email_type,
                redirect_organization_code=self.organization.code,
            )
            if email_sent:
                template_path = "execute_actions_email_success.html"
            else:
                template_path = "execute_actions_email_not_sent.html"
            with translation.override(user.language):
                return render(request, f"authentication/{template_path}")
        except Exception as e:  # noqa: PIE786
            with translation.override(user.language):
                return render(
                    request,
                    "authentication/execute_actions_email_error.html",
                    {"error": e},
                )


class PeopleGroupViewSet(
    MultipleIDViewset, OrganizationRelatedViewset, viewsets.ModelViewSet
):
    queryset = PeopleGroup.objects.all()
    serializer_class = PeopleGroupSerializer
    filterset_class = PeopleGroupFilter
    lookup_field = "id"
    search_fields = ["name"]
    filter_backends = (
        TrigramSearchFilter,
        DjangoFilterBackend,
        OrderingFilter,
    )
    multiple_lookup_fields = [
        (PeopleGroup, "id"),
    ]

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
        organization = Prefetch(
            "organization",
            queryset=Organization.objects.select_related(
                "faq", "parent", "banner_image", "logo_image"
            ).prefetch_related("wikipedia_tags"),
        )
        return self.request.user.get_people_group_queryset(organization).filter(
            organization=self.organization, is_root=False
        )

    def get_serializer_class(self):
        if self.action == "list":
            return PeopleGroupLightSerializer
        return self.serializer_class

    def google_sync(self, instance, data):
        create_in_google = data.get("create_in_google", False)
        exists_in_google = GoogleGroup.objects.filter(people_group=instance).exists()
        if create_in_google and not exists_in_google:
            create_google_group(instance)
        elif not create_in_google and exists_in_google:
            update_google_group(instance)
        instance.refresh_from_db()

    def create(self, request, *args, **kwargs):
        try:
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
        managers_ids = group.managers.all().values_list("id", flat=True)
        leaders_ids = group.leaders.all().values_list("id", flat=True)
        queryset = (
            group.get_all_members()
            .distinct()
            .annotate(
                is_leader=Case(
                    When(id__in=leaders_ids, then=True), default=Value(False)
                )
            )
            .annotate(
                is_manager=Case(
                    When(id__in=managers_ids, then=True), default=Value(False)
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
        group_projects_ids = (
            Project.objects.filter(groups__people_groups=group)
            .distinct()
            .values_list("id", flat=True)
        )
        queryset = (
            self.request.user.get_project_queryset(categories)
            .filter(Q(groups__people_groups=group) | Q(people_groups=group))
            .annotate(
                is_group_project=Case(
                    When(id__in=group_projects_ids, then=True), default=Value(False)
                ),
                is_featured=Case(
                    When(people_groups=group, then=True), default=Value(False)
                ),
            )
            .distinct()
            .order_by("-is_featured", "-is_group_project")
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
        return Response(people_group.get_hierarchy(), status=status.HTTP_200_OK)


@extend_schema(
    parameters=[OpenApiParameter("people_group_id", str, OpenApiParameter.PATH)]
)
class PeopleGroupHeaderView(
    MultipleIDViewset, DetailOnlyViewset, PeopleGroupRelatedViewSet, ImageStorageView
):
    permission_classes = [
        IsAuthenticatedOrReadOnly,
        ReadOnly
        | IsOwner
        | HasBasePermission("change_peoplegroup", "accounts")
        | HasOrganizationPermission("change_peoplegroup")
        | HasPeopleGroupPermission("change_peoplegroup"),
    ]
    queryset = Image.objects.all()
    lookup_field = "id"
    lookup_value_regex = "[0-9]+"
    model_people_group_field = "people_group_header"
    multiple_lookup_fields = [
        (PeopleGroup, "people_group_id"),
    ]

    @staticmethod
    def upload_to(instance, filename) -> str:
        return f"people_group/header/{uuid.uuid4()}#{instance.name}"

    def add_image_to_model(self, image):
        self.people_group.header_image = image
        self.people_group.save()
        return f"/v1/people-group/{self.people_group.id}/header"


@extend_schema(
    parameters=[OpenApiParameter("people_group_id", str, OpenApiParameter.PATH)]
)
class PeopleGroupLogoView(
    MultipleIDViewset, DetailOnlyViewset, PeopleGroupRelatedViewSet, ImageStorageView
):
    permission_classes = [
        IsAuthenticatedOrReadOnly,
        ReadOnly
        | IsOwner
        | HasBasePermission("change_peoplegroup", "accounts")
        | HasOrganizationPermission("change_peoplegroup")
        | HasPeopleGroupPermission("change_peoplegroup"),
    ]
    queryset = Image.objects.all()
    lookup_field = "id"
    lookup_value_regex = "[0-9]+"
    model_people_group_field = "people_group_logo"
    multiple_lookup_fields = [
        (PeopleGroup, "people_group_id"),
    ]

    @staticmethod
    def upload_to(instance, filename) -> str:
        return f"people_group/logo/{uuid.uuid4()}#{instance.name}"

    def add_image_to_model(self, image):
        self.people_group.logo_image = image
        self.people_group.save()
        return f"/v1/people-group/{self.people_group.id}/logo"


class SkillViewSet(UserRelatedViewSet, viewsets.ModelViewSet):
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
            raise SkillAlreadyAddedError


class UserProfilePictureView(MultipleIDViewset, UserRelatedViewSet, ImageStorageView):
    permission_classes = [
        IsAuthenticatedOrReadOnly,
        ReadOnly
        | IsOwner
        | WillBeOwner
        | HasBasePermission("change_projectuser", "accounts")
        | HasOrganizationPermission("change_projectuser"),
    ]
    queryset = Image.objects.all()
    multiple_lookup_fields = [
        (ProjectUser, "user_id"),
    ]

    @staticmethod
    def upload_to(instance, filename) -> str:
        return f"account/profile/{uuid.uuid4()}#{instance.name}"

    def add_image_to_model(self, image):
        self.user.profile_picture = image
        self.user.save()
        image.owner = self.user
        image.save()
        return f"/v1/user/{self.user.id}/profile-picture/{image.id}"


class PrivacySettingsViewSet(
    MultipleIDViewset, UserRelatedViewSet, RetrieveUpdateModelViewSet
):
    """Allows getting or modifying a user's privacy settings."""

    permission_classes = [
        IsAuthenticatedOrReadOnly,
        ReadOnly
        | IsOwner
        | HasBasePermission("change_projectuser", "accounts")
        | HasOrganizationPermission("change_projectuser"),
    ]
    serializer_class = PrivacySettingsSerializer
    queryset = PrivacySettings.objects.all()
    lookup_field = "user_id"
    lookup_url_kwarg = "user_id"
    multiple_lookup_fields = [
        (ProjectUser, "user_id"),
    ]


class DeleteCookieView(views.APIView):
    @extend_schema(request=None, responses=EmptyPayloadResponseSerializer)
    def get(self, request, *args, **kwargs):
        access_token = request.COOKIES.get(settings.JWT_ACCESS_TOKEN_COOKIE_NAME, None)
        if not access_token:
            return HttpResponse("Cookie already deleted")
        response = HttpResponse("Cookie deleted")
        response.delete_cookie(settings.JWT_ACCESS_TOKEN_COOKIE_NAME, samesite="None")
        return response


class AccessTokenView(APIView):
    @extend_schema(request=CredentialsSerializer, responses=AccessTokenSerializer)
    def post(self, request):
        serializer = CredentialsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = KeycloakService.get_token_for_user(
            request.data["username"], request.data["password"]
        )
        return Response(AccessTokenSerializer(token).data)
