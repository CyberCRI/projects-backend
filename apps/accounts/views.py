import uuid

from django.conf import settings
from django.db import transaction
from django.db.models import Case, Prefetch, Q, QuerySet, Value, When
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
from keycloak import (
    KeycloakDeleteError,
    KeycloakGetError,
    KeycloakPostError,
    KeycloakPutError,
)
from rest_framework import status, views, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.parsers import JSONParser
from rest_framework.permissions import (
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)
from rest_framework.response import Response
from rest_framework.serializers import BooleanField
from rest_framework.views import APIView

from apps.commons.filters import UnaccentSearchFilter
from apps.commons.models import GroupData
from apps.commons.permissions import IsOwner, ReadOnly, WillBeOwner
from apps.commons.serializers import (
    EmailAddressSerializer,
    RetrieveUpdateModelViewSet,
)
from apps.commons.utils import map_action_to_permission
from apps.commons.views import DetailOnlyViewsetMixin, MultipleIDViewsetMixin
from apps.files.models import Image
from apps.files.views import ImageStorageView
from apps.organizations.models import Organization
from apps.organizations.permissions import HasOrganizationPermission
from apps.projects.serializers import LocationSerializer, ProjectLightSerializer
from apps.skills.models import Skill
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

from .exceptions import EmailTypeMissingError, PermissionNotFoundError
from .filters import PeopleGroupFilter, UserFilter
from .models import AnonymousUser, PeopleGroup, PrivacySettings, ProjectUser
from .parsers import UserMultipartParser
from .permissions import HasBasePermission, HasPeopleGroupPermission
from .serializers import (
    AccessTokenSerializer,
    CredentialsSerializer,
    EmptyPayloadResponseSerializer,
    PeopleGroupAddFeaturedProjectsSerializer,
    PeopleGroupAddTeamMembersSerializer,
    PeopleGroupHierarchySerializer,
    PeopleGroupLightSerializer,
    PeopleGroupRemoveFeaturedProjectsSerializer,
    PeopleGroupRemoveTeamMembersSerializer,
    PeopleGroupSerializer,
    PrivacySettingsSerializer,
    UserAdminListSerializer,
    UserLighterSerializer,
    UserLightSerializer,
    UserSerializer,
)
from .tasks import update_new_user_pending_access_requests
from .utils import (
    account_sync_errors_handler,
    get_default_group,
    get_permission_from_representation,
)


class UserViewSet(MultipleIDViewsetMixin, viewsets.ModelViewSet):
    serializer_class = UserSerializer
    lookup_field = "id"
    lookup_value_regex = (
        "[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|[a-zA-Z0-9_-]{1,}"
    )
    search_fields = [
        "given_name",
        "family_name",
        "email",
        "job",
    ]
    parser_classes = (JSONParser, UserMultipartParser)
    filter_backends = (
        UnaccentSearchFilter,
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
                    then=Value(GroupData.Role.ADMINS),
                ),
                When(
                    pk__in=organization.facilitators.values_list("pk", flat=True),
                    then=Value(GroupData.Role.FACILITATORS),
                ),
                When(
                    pk__in=organization.users.values_list("pk", flat=True),
                    then=Value(GroupData.Role.USERS),
                ),
                When(
                    pk__in=organization.viewers.values_list("pk", flat=True),
                    then=Value(GroupData.Role.VIEWERS),
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
        organization_pk = self.request.query_params.get("current_org_pk")
        if organization_pk is not None:
            organization = Organization.objects.get(pk=organization_pk)
            queryset = self.annotate_organization_role(queryset, organization)
        if self.action == "admin_list":
            queryset = self.annotate_keycloak_email_verified(queryset)
        skills_prefetch = Prefetch(
            "skills", queryset=Skill.objects.select_related("tag")
        )
        return queryset.prefetch_related(
            skills_prefetch,
            "groups",
        ).select_related("researcher")

    def get_object(self):
        """
        Returns the object the view is displaying.

        Overridden to add the organization role to the user if they have logged in
        through an IdP for the first time.

        This would be better if it was done during authentication but it slows down
        every authenticated request instead of just this one.

        This might cause some issues on the first login, because some other requests
        might be made before this one and the organization role would not be added yet.
        """
        instance: ProjectUser = super().get_object()
        if self.request.user.is_authenticated and instance.id == self.request.user.id:
            instance = instance.add_idp_organizations()
        return instance

    def get_serializer_class(self):
        if self.action == "list":
            return UserLightSerializer
        if self.action == "admin_list":
            return UserAdminListSerializer
        return self.serializer_class

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        current_org_pk = self.request.query_params.get("current_org_pk")
        if current_org_pk:
            organization = get_object_or_404(Organization, pk=current_org_pk)
            context.update({"organization": organization})
        return context

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="current_org_pk",
                description="Organization id used to fetch the role of the users in the organization",
                required=False,
                type=str,
            )
        ],
    )
    @action(
        detail=False,
        methods=["GET"],
        url_path="get-by-email/(?P<email>[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+.[a-zA-Z0-9-.]+)",
        url_name="get-by-email",
        permission_classes=[HasBasePermission("get_user_by_email", "accounts")],
    )
    def get_by_email(self, request, *args, **kwargs):
        queryset = ProjectUser.objects.all()
        current_org_pk = request.query_params.get("current_org_pk")
        if current_org_pk is not None:
            organization = Organization.objects.get(pk=current_org_pk)
            queryset = self.annotate_organization_role(queryset, organization)
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
                redirect_organization_code = self.request.query_params.get(
                    "organization", "DEFAULT"
                )

            instance = self.google_sync(instance, self.request.data, True)
            keycloak_account = KeycloakService.create_user(
                instance, self.request.data.get("password")
            )
        update_new_user_pending_access_requests.delay(
            instance.id, redirect_organization_code
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
            redirect_organization_code = request.query_params.get(
                "organization", "DEFAULT"
            )
            KeycloakService.send_email(
                keycloak_account=user.keycloak_account,
                email_type=KeycloakService.EmailType.FORCE_RESET_PASSWORD,
                actions=["UPDATE_PASSWORD"],
                redirect_organization_code=redirect_organization_code,
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
            redirect_organization_code = request.query_params.get(
                "organization", "DEFAULT"
            )
            email_type = request.query_params.get("email_type")
            if not email_type:
                raise EmailTypeMissingError
            if not hasattr(user, "keycloak_account"):
                raise KeycloakAccountNotFound
            email_sent = KeycloakService.send_email(
                keycloak_account=user.keycloak_account,
                email_type=email_type,
                redirect_organization_code=redirect_organization_code,
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


class PeopleGroupViewSet(MultipleIDViewsetMixin, viewsets.ModelViewSet):
    queryset = PeopleGroup.objects.all()
    serializer_class = PeopleGroupSerializer
    filterset_class = PeopleGroupFilter
    lookup_field = "id"
    search_fields = ["name"]
    filter_backends = (
        UnaccentSearchFilter,
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
        if "organization_code" in self.kwargs:
            return (
                self.request.user.get_people_group_queryset()
                .filter(
                    organization__code=self.kwargs["organization_code"],
                    is_root=False,
                )
                .select_related("organization")
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
        exists_in_google = GoogleGroup.objects.filter(people_group=instance).exists()
        if create_in_google and not exists_in_google:
            create_google_group(instance)
        elif not create_in_google and exists_in_google:
            update_google_group(instance)
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

        modules_manager = group.get_related_module()
        modules = modules_manager(group, request.user)
        queryset = modules.members()

        page = self.paginate_queryset(queryset)
        if page is not None:
            user_serializer = UserLighterSerializer(
                page, many=True, context={"request": request}
            )
            return self.get_paginated_response(user_serializer.data)

        user_serializer = UserLighterSerializer(
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
        responses=ProjectLightSerializer(many=True),
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
        ],
    )
    @action(
        detail=True,
        methods=["GET"],
        url_path="project",
        permission_classes=[ReadOnly],
    )
    def project(self, request, *args, **kwargs):
        group = self.get_object()
        modules_manager = group.get_related_module()
        modules = modules_manager(group, request.user)
        queryset = modules.featured_projects()

        page = self.paginate_queryset(queryset)
        project_serializer = ProjectLightSerializer(
            page, context={"request": request}, many=True
        )
        return self.get_paginated_response(project_serializer.data)

    @extend_schema(responses=PeopleGroupHierarchySerializer)
    @action(
        detail=True,
        methods=["GET"],
        url_path="hierarchy",
        permission_classes=[ReadOnly],
    )
    def hierarchy(self, request, *args, **kwargs):
        people_group = self.get_object()
        return Response(
            PeopleGroupHierarchySerializer(
                people_group, context={"request": request}
            ).data,
            status=status.HTTP_200_OK,
        )

    @extend_schema(responses=PeopleGroupLightSerializer(many=True))
    @action(
        detail=True,
        methods=["GET"],
        url_path="subgroups",
        permission_classes=[ReadOnly],
    )
    def subgroups(self, request, *args, **kwargs):
        group = self.get_object()
        modules_manager = group.get_related_module()
        modules = modules_manager(group, request.user)
        queryset = modules.subgroups()

        queryset_page = self.paginate_queryset(queryset)
        data = PeopleGroupLightSerializer(
            queryset_page, many=True, context={"request": request}
        )
        return self.get_paginated_response(data.data)

    @extend_schema(responses=PeopleGroupLightSerializer(many=True))
    @action(
        detail=True,
        methods=["GET"],
        url_path="similars",
        permission_classes=[ReadOnly],
    )
    def similars(self, request, *args, **kwargs):
        group = self.get_object()
        modules_manager = group.get_related_module()
        modules = modules_manager(group, request.user)
        queryset = modules.similars()

        queryset_page = self.paginate_queryset(queryset)
        data = PeopleGroupLightSerializer(
            queryset_page, many=True, context={"request": request}
        )
        return self.get_paginated_response(data.data)

    @action(
        detail=True,
        methods=["GET"],
        url_path="locations",
        permission_classes=[ReadOnly],
    )
    def locations(self, request, *args, **kwargs):
        group = self.get_object()
        modules_manager = group.get_related_module()
        modules = modules_manager(group, request.user)
        queryset = modules.locations()

        return Response(
            LocationSerializer(queryset, many=True, context={"request": request}).data,
            status=status.HTTP_200_OK,
        )


@extend_schema(
    parameters=[OpenApiParameter("people_group_id", str, OpenApiParameter.PATH)]
)
class PeopleGroupHeaderView(
    MultipleIDViewsetMixin, DetailOnlyViewsetMixin, ImageStorageView
):
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
    multiple_lookup_fields = [
        (PeopleGroup, "people_group_id"),
    ]

    def get_queryset(self):
        if all(k in self.kwargs for k in ["people_group_id", "organization_code"]):
            return Image.objects.filter(
                people_group_header__id=self.kwargs["people_group_id"],
                people_group_header__organization__code=self.kwargs[
                    "organization_code"
                ],
            )
        return Image.objects.none()

    @staticmethod
    def upload_to(instance, filename) -> str:
        return f"people_group/header/{uuid.uuid4()}#{instance.name}"

    def add_image_to_model(self, image):
        if all(k in self.kwargs for k in ["people_group_id", "organization_code"]):
            people_group = PeopleGroup.objects.get(
                organization__code=self.kwargs["organization_code"],
                id=self.kwargs["people_group_id"],
            )
            people_group.header_image = image
            people_group.save()
            return f"/v1/organization/{people_group.organization.code}/people-group/{people_group.id}/header"
        return None


@extend_schema(
    parameters=[OpenApiParameter("people_group_id", str, OpenApiParameter.PATH)]
)
class PeopleGroupLogoView(
    MultipleIDViewsetMixin, DetailOnlyViewsetMixin, ImageStorageView
):
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
    multiple_lookup_fields = [
        (PeopleGroup, "people_group_id"),
    ]

    def get_queryset(self):
        if all(k in self.kwargs for k in ["people_group_id", "organization_code"]):
            return Image.objects.filter(
                people_group_logo__id=self.kwargs["people_group_id"],
                people_group_logo__organization__code=self.kwargs["organization_code"],
            )
        return Image.objects.none()

    @staticmethod
    def upload_to(instance, filename) -> str:
        return f"people_group/logo/{uuid.uuid4()}#{instance.name}"

    def add_image_to_model(self, image):
        if all(k in self.kwargs for k in ["people_group_id", "organization_code"]):
            people_group = PeopleGroup.objects.get(
                organization__code=self.kwargs["organization_code"],
                id=self.kwargs["people_group_id"],
            )
            people_group.logo_image = image
            people_group.save()
            return f"/v1/organization/{people_group.organization.code}/people-group/{people_group.id}/logo"
        return None


class DeleteCookieView(views.APIView):
    @extend_schema(request=None, responses=EmptyPayloadResponseSerializer)
    def get(self, request, *args, **kwargs):
        access_token = request.COOKIES.get(settings.JWT_ACCESS_TOKEN_COOKIE_NAME)
        if not access_token:
            return HttpResponse("Cookie already deleted")
        response = HttpResponse("Cookie deleted")
        response.delete_cookie(settings.JWT_ACCESS_TOKEN_COOKIE_NAME, samesite="None")
        return response


class UserProfilePictureView(MultipleIDViewsetMixin, ImageStorageView):
    permission_classes = [
        IsAuthenticatedOrReadOnly,
        ReadOnly
        | IsOwner
        | WillBeOwner
        | HasBasePermission("change_projectuser", "accounts")
        | HasOrganizationPermission("change_projectuser"),
    ]
    multiple_lookup_fields = [
        (ProjectUser, "user_id"),
    ]

    def get_queryset(self):
        if "user_id" in self.kwargs:
            return Image.objects.filter(user=self.kwargs["user_id"])
        return Image.objects.none()

    @staticmethod
    def upload_to(instance, filename) -> str:
        return f"account/profile/{uuid.uuid4()}#{instance.name}"

    def add_image_to_model(self, image):
        if "user_id" in self.kwargs:
            user = ProjectUser.objects.get(id=self.kwargs["user_id"])
            user.profile_picture = image
            user.save()
            image.owner = user
            image.save()
            return f"/v1/user/{self.kwargs['user_id']}/profile-picture/{image.id}"
        return None


class PrivacySettingsViewSet(MultipleIDViewsetMixin, RetrieveUpdateModelViewSet):
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
    lookup_url_kwarg = "user_id"
    multiple_lookup_fields = [
        (ProjectUser, "user_id"),
    ]

    def get_queryset(self):
        if "user_id" in self.kwargs:
            qs = self.request.user.get_user_related_queryset(
                PrivacySettings.objects.all()
            )
            return qs.filter(user__id=self.kwargs["user_id"])
        return PrivacySettings.objects.none()


class AccessTokenView(APIView):
    @extend_schema(request=CredentialsSerializer, responses=AccessTokenSerializer)
    def post(self, request):
        serializer = CredentialsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = KeycloakService.get_token_for_user(
            request.data["username"], request.data["password"]
        )
        return Response(AccessTokenSerializer(token).data)
