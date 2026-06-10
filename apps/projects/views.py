import enum
import uuid

from django.apps import apps
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.db.models import QuerySet
from django.shortcuts import get_object_or_404, redirect
from django.utils.decorators import method_decorator
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import (
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)
from rest_framework.response import Response
from simple_history.utils import update_change_reason

from apps.accounts.models import ProjectUser
from apps.accounts.permissions import HasBasePermission
from apps.analytics.models import Stat
from apps.commons.cache import clear_cache_with_key, redis_cache_view
from apps.commons.permissions import IsOwner, ReadOnly
from apps.commons.utils import map_action_to_permission
from apps.commons.views import (
    MultipleIDViewsetMixin,
    NestedProjectTabViewMixins,
    NestedProjectViewMixins,
)
from apps.files.models import Image
from apps.files.views import ImageStorageView
from apps.notifications.tasks import (
    notify_group_as_member_added,
    notify_group_member_deleted,
    notify_member_added,
    notify_member_deleted,
    notify_member_updated,
    notify_new_blogentry,
    notify_new_private_message,
    notify_ready_for_review,
)
from apps.organizations.permissions import HasOrganizationPermission
from apps.organizations.utils import get_below_hierarchy_codes
from apps.projects.exceptions import (
    LinkedProjectPermissionDeniedError,
    OrganizationsParameterMissing,
)

from .filters import ProjectFilter, ProjectGroupsFilter, ProjectMembersFilter
from .models import (
    BlogEntry,
    LinkedProject,
    Project,
    ProjectMessage,
    ProjectTab,
    ProjectTabItem,
)
from .permissions import HasProjectPermission, ProjectIsNotLocked
from .serializers import (
    BlogEntrySerializer,
    GoalSerializer,
    LinkedProjectSerializer,
    LocationSerializer,
    ProjectAddTeamMembersSerializer,
    ProjectGroupSerializer,
    ProjectLightSerializer,
    ProjectMessageSerializer,
    ProjectRemoveLinkedProjectSerializer,
    ProjectRemoveTeamMembersSerializer,
    ProjectSerializer,
    ProjectSuperLightSerializer,
    ProjectTabItemSerializer,
    ProjectTabSerializer,
    ProjectTeamMembersSerializer,
    ProjectVersionListSerializer,
    ProjectVersionSerializer,
)


class ProjectViewSet(MultipleIDViewsetMixin, viewsets.ModelViewSet):
    """Main endpoints for projects."""

    class InfoDetails(enum.Enum):
        SUMMARY = "summary"

    serializer_class = ProjectSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = ProjectFilter
    ordering_fields = ["created_at", "updated_at"]
    lookup_field = "id"
    lookup_value_regex = "[^/]+"
    multiple_lookup_fields = [(Project, "id")]

    def get_permissions(self):
        codename = map_action_to_permission(self.action, "project")
        if codename:
            self.permission_classes = [
                IsAuthenticatedOrReadOnly,
                ProjectIsNotLocked,
                ReadOnly
                | HasBasePermission(codename, "projects")
                | HasOrganizationPermission(codename)
                | HasProjectPermission(codename),
            ]
        return super().get_permissions()

    def get_queryset(self) -> QuerySet:
        return (
            self.request.user.get_project_queryset()
            .select_related("header_image")
            .prefetch_related(
                "categories",
                "tags",
                "organizations",
            )
        )

    def get_serializer_class(self):
        is_summary = (
            self.request.query_params.get("info_details")
            == ProjectViewSet.InfoDetails.SUMMARY
        )
        if self.action == "list" or is_summary:
            return ProjectLightSerializer
        return self.serializer_class

    def get_serializer_context(self):
        """Adds request to the serializer's context."""
        return {"request": self.request}

    def perform_create(self, serializer: ProjectSerializer):
        project = serializer.save()
        project.setup_permissions(self.request.user)
        Stat(project=project).save()
        project._change_reason = "Created project"
        project.save()

    @transaction.atomic
    def perform_update(self, serializer: ProjectSerializer):
        project = serializer.save()
        changes = serializer.validated_data
        fields = sorted(changes.keys())
        update_change_reason(project, f"Updated: {' + '.join(fields)}"[:100])
        if (
            settings.ENABLE_CACHE
            and changes.get("publication_status")
            and project.announcements.exists()
        ):
            cache.delete_many(cache.keys("announcements_list_cache*"))
        if changes.get("life_status", "") == Project.LifeStatus.TO_REVIEW:
            notify_ready_for_review.delay(project.pk, self.request.user.pk)
        return project

    def perform_destroy(self, instance):
        if settings.ENABLE_CACHE and instance.announcements.exists():
            cache.delete_many(cache.keys("announcements_list_cache*"))
        super().perform_destroy(instance)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="info_details",
                description='set this parameter to "summary" to get less details '
                "about the project",
                required=False,
                type=str,
            )
        ]
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "id",
                location=OpenApiParameter.PATH,
                description="ID of the project to duplicate",
            )
        ],
        responses={201: ProjectSerializer},
    )
    @action(
        detail=True,
        methods=["POST"],
        permission_classes=[
            IsAuthenticated,
            HasBasePermission("duplicate_project", "projects")
            | HasOrganizationPermission("duplicate_project")
            | HasProjectPermission("duplicate_project"),
        ],
    )
    def duplicate(self, request, *args, **kwargs):
        """Duplicate a given project."""
        project = self.get_object()
        duplicated_project = project.duplicate(owner=request.user)
        context = {"request": request}
        return Response(
            ProjectSerializer(duplicated_project, context=context).data,
            status=status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=["DELETE"],
        url_path="quit",
        permission_classes=[IsAuthenticated],
    )
    @transaction.atomic
    def remove_self(self, request, *args, **kwargs):
        """Remove users from the project's group of the given name."""
        project = self.get_object()
        serializer = ProjectRemoveTeamMembersSerializer(
            data={"project": project.pk, "users": [request.user.id]}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        project._change_reason = "Removed members"
        project.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _toggle_is_locked(self, value):
        project = self.get_object()
        project.is_locked = value
        project.save()
        return Response(status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["POST"],
        permission_classes=[
            IsAuthenticated,
            HasBasePermission("lock_project", "projects")
            | HasOrganizationPermission("lock_project")
            | HasProjectPermission("lock_project"),
        ],
    )
    def lock(self, request, *args, **kwargs):
        return self._toggle_is_locked(value=True)

    @action(
        detail=True,
        methods=["POST"],
        permission_classes=[
            IsAuthenticated,
            HasBasePermission("lock_project", "projects")
            | HasOrganizationPermission("lock_project")
            | HasProjectPermission("lock_project"),
        ],
    )
    def unlock(self, request, *args, **kwargs):
        return self._toggle_is_locked(value=False)

    @extend_schema(
        responses=ProjectSuperLightSerializer(many=True),
        parameters=[
            OpenApiParameter(
                name="threshold",
                description="Maximum number of results.",
                required=False,
                type=int,
                default=5,
            ),
            OpenApiParameter(
                name="organizations",
                description="list of organization codes.",
                required=False,
                many=True,
                type=str,
            ),
        ],
    )
    @action(detail=True, methods=["GET"], permission_classes=[ReadOnly])
    def similar(self, request, *args, **kwargs):
        organizations = request.query_params.getlist("organizations")
        if not organizations:
            raise OrganizationsParameterMissing

        project = self.get_object()

        queryset = (
            project.modules_by_user(request.user)
            .similars()
            .filter(organizations__code__in=get_below_hierarchy_codes(organizations))
        )

        page = self.paginate_queryset(queryset)
        serializer = ProjectSuperLightSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)


class ProjectHeaderView(NestedProjectViewMixins, ImageStorageView):
    permission_classes = [
        IsAuthenticatedOrReadOnly,
        ProjectIsNotLocked,
        ReadOnly
        | IsOwner
        | HasBasePermission("change_project", "projects")
        | HasOrganizationPermission("change_project")
        | HasProjectPermission("change_project"),
    ]

    def get_queryset(self):
        return Image.objects.filter(project_header=self.project)

    @staticmethod
    def upload_to(instance, filename) -> str:
        return f"project/header/{uuid.uuid4()}#{instance.name}"

    def add_image_to_model(self, image):
        self.project.header_image = image
        self.project.save()
        return f"/v1/project/{self.project}/header/{image.id}"


class ProjectImagesView(NestedProjectViewMixins, ImageStorageView):
    permission_classes = [
        IsAuthenticatedOrReadOnly,
        ProjectIsNotLocked,
        ReadOnly
        | IsOwner
        | HasBasePermission("change_project", "projects")
        | HasOrganizationPermission("change_project")
        | HasProjectPermission("change_project"),
    ]

    def get_queryset(self):
        qs = self.project.images.all()
        # Retrieve images before project is posted
        if self.request.user.is_authenticated:
            qs = qs | Image.objects.filter(owner=self.request.user)
        return qs.distinct()

    @staticmethod
    def upload_to(instance, filename) -> str:
        return f"project/images/{uuid.uuid4()}#{instance.name}"

    def retrieve(self, request, *args, **kwargs):
        image = self.get_object()
        return redirect(image.file.url)

    def add_image_to_model(self, image, *args, **kwargs):
        self.project.images.add(image)
        self.project.save()
        return f"/v1/project/{self.project.id}/image/{image.id}"


class ProjectMemberViewSet(
    NestedProjectViewMixins,
    viewsets.ModelViewSet,
):
    serializer_class = ProjectTeamMembersSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = ProjectMembersFilter
    lookup_field = "id"
    ordering_fields = ("role",)
    lookup_value_regex = "[0-9]+"
    permission_classes = [
        IsAuthenticatedOrReadOnly,
        ProjectIsNotLocked,
        ReadOnly
        | HasBasePermission("change_project", "projects")
        | HasOrganizationPermission("change_project")
        | HasProjectPermission("change_project"),
    ]

    def get_queryset(self) -> QuerySet[ProjectUser]:
        return self.project.modules_by_user(self.request.user).members()

    @extend_schema(request=ProjectAddTeamMembersSerializer, responses=ProjectSerializer)
    @action(
        detail=False,
        methods=["POST"],
        url_path="add",
        permission_classes=[
            IsAuthenticated,
            ProjectIsNotLocked,
            HasBasePermission("change_project", "projects")
            | HasOrganizationPermission("change_project")
            | HasProjectPermission("change_project"),
        ],
    )
    @transaction.atomic
    def add_member(self, request, *args, **kwargs):
        """Add users to the project's group of the given name or add group to project.member_groups."""
        serializer = ProjectAddTeamMembersSerializer(
            data={"project": self.project.pk, **request.data}
        )
        serializer.is_valid(raise_exception=True)
        instances = serializer.save()
        self.notify_add_members(instances)
        self.project.refresh_from_db()
        self.project._change_reason = "Added members"
        self.project.save()

        return Response(status=status.HTTP_204_NO_CONTENT)

    def notify_add_members(self, instances):
        for instance in instances:
            if instance["type"] == "projectuser":
                notification = (
                    notify_member_added
                    if instance["created"]
                    else notify_member_updated
                )
                notification.delay(
                    instance["project"].pk,
                    instance["user"].pk,
                    self.request.user.pk,
                    instance["role"],
                )
            if instance["type"] == "peoplegroup" and instance["created"]:
                notify_group_as_member_added.delay(
                    instance["project"].pk,
                    instance["people_group"].pk,
                    self.request.user.pk,
                    instance["role"],
                )

    @extend_schema(
        request=ProjectRemoveTeamMembersSerializer, responses=ProjectSerializer
    )
    @action(
        detail=False,
        methods=["POST"],
        url_path="remove",
        permission_classes=[
            IsAuthenticated,
            ProjectIsNotLocked,
            HasBasePermission("change_project", "projects")
            | HasOrganizationPermission("change_project")
            | HasProjectPermission("change_project"),
        ],
    )
    @transaction.atomic
    def remove_member(self, request, *args, **kwargs):
        """Remove users from the project's group of the given name."""
        # The following 3 lines are here for backward compatibility
        data = request.data.copy()
        if "user" in data and "users" not in data:
            data = {"users": [data["user"]]}
        serializer = ProjectRemoveTeamMembersSerializer(
            data={"project": self.project.pk, **data}
        )
        serializer.is_valid(raise_exception=True)
        instances = serializer.save()
        self.notify_remove_members(instances)
        self.project.refresh_from_db()
        self.project._change_reason = "Removed members"
        self.project.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    def notify_remove_members(self, instances):
        for user in instances["users"]:
            notify_member_deleted.delay(
                instances["project"].pk, user.pk, self.request.user.pk
            )
        for people_group in instances["people_groups"]:
            notify_group_member_deleted.delay(
                instances["project"].pk, people_group.pk, self.request.user.pk
            )


class ProjectGroupViewSet(
    NestedProjectViewMixins,
    viewsets.ModelViewSet,
):
    serializer_class = ProjectGroupSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_class = ProjectGroupsFilter
    lookup_field = "id"
    ordering_fields = ("role",)
    lookup_value_regex = "[0-9]+"
    permission_classes = [
        IsAuthenticatedOrReadOnly,
        ProjectIsNotLocked,
        ReadOnly
        | HasBasePermission("change_project", "projects")
        | HasOrganizationPermission("change_project")
        | HasProjectPermission("change_project"),
    ]

    def get_queryset(self) -> QuerySet:
        return (
            self.project.modules_by_user(self.request.user)
            .groups()
            .select_related("organization")
        )


class BlogEntryViewSet(NestedProjectViewMixins, viewsets.ModelViewSet):
    serializer_class = BlogEntrySerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ("created_at", "updated_at")
    lookup_field = "id"
    lookup_value_regex = "[0-9]+"
    permission_classes = [
        IsAuthenticatedOrReadOnly,
        ProjectIsNotLocked,
        ReadOnly
        | HasBasePermission("change_project", "projects")
        | HasOrganizationPermission("change_project")
        | HasProjectPermission("change_project"),
    ]

    def get_queryset(self) -> QuerySet:
        return (
            self.project.modules_by_user(self.request.user)
            .blogs()
            .prefetch_related("images")
        )

    def perform_create(self, serializer):
        instance = serializer.save()
        notify_new_blogentry.delay(instance.pk, self.request.user.pk)


class BlogEntryImagesView(NestedProjectViewMixins, ImageStorageView):
    permission_classes = [
        IsAuthenticatedOrReadOnly,
        ProjectIsNotLocked,
        ReadOnly
        | IsOwner
        | HasBasePermission("change_project", "projects")
        | HasOrganizationPermission("change_project")
        | HasProjectPermission("change_project"),
    ]

    def get_queryset(self):
        blogs_qs = self.project.modules_by_user(self.request.user).blogs()

        qs = Image.objects.filter(blog_entries__in=blogs_qs)
        # Retrieve images before blog entry is posted
        if self.request.user.is_authenticated:
            qs = qs | Image.objects.filter(owner=self.request.user)
        return qs.distinct()

    @staticmethod
    def upload_to(instance, filename) -> str:
        return f"blog_entry/images/{uuid.uuid4()}#{instance.name}"

    def retrieve(self, request, *args, **kwargs):
        image = self.get_object()
        return redirect(image.file.url)

    def add_image_to_model(self, image, *args, **kwargs):
        if "blog_entry_id" in self.request.query_params:
            blog_entry = BlogEntry.objects.get(
                project=self.project,
                id=self.request.query_params["blog_entry_id"],
            )
            blog_entry.images.add(image)
            blog_entry.save()
        return f"/v1/project/{self.project.id}/blog-entry-image/{image.id}"


class GoalViewSet(NestedProjectViewMixins, viewsets.ModelViewSet):
    serializer_class = GoalSerializer
    filter_backends = [DjangoFilterBackend]
    lookup_field = "id"
    lookup_value_regex = "[0-9]+"
    permission_classes = [
        IsAuthenticatedOrReadOnly,
        ProjectIsNotLocked,
        ReadOnly
        | HasBasePermission("change_project", "projects")
        | HasOrganizationPermission("change_project")
        | HasProjectPermission("change_project"),
    ]

    def get_queryset(self) -> QuerySet:
        return self.project.modules_by_user(self.request.user).goals()


class LocationViewSet(NestedProjectViewMixins, viewsets.ModelViewSet):
    serializer_class = LocationSerializer
    lookup_field = "id"
    lookup_value_regex = "[0-9]+"
    pagination_class = None
    permission_classes = [
        IsAuthenticatedOrReadOnly,
        ProjectIsNotLocked,
        ReadOnly
        | HasBasePermission("change_project", "projects")
        | HasOrganizationPermission("change_project")
        | HasProjectPermission("change_project"),
    ]

    def get_queryset(self):
        return self.project.modules_by_user(self.request.user).locations()

    @method_decorator(
        redis_cache_view("locations_list_cache", settings.CACHE_LOCATIONS_LIST_TTL)
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @method_decorator(clear_cache_with_key("locations_list_cache"))
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)


class HistoricalProjectViewSet(NestedProjectViewMixins, viewsets.ReadOnlyModelViewSet):
    lookup_field = "pk"
    permission_classes = [ReadOnly]

    def get_serializer_class(self):
        if self.action == "list":
            return ProjectVersionListSerializer
        return ProjectVersionSerializer

    def get_queryset(self) -> QuerySet:
        return apps.get_model("projects", "HistoricalProject").objects.filter(
            history_relation=self.project, history_change_reason__isnull=False
        )


class LinkedProjectViewSet(NestedProjectViewMixins, viewsets.ModelViewSet):
    serializer_class = LinkedProjectSerializer
    lookup_field = "id"
    lookup_value_regex = "[0-9]+"
    permission_classes = [
        IsAuthenticatedOrReadOnly,
        ProjectIsNotLocked,
        ReadOnly
        | HasBasePermission("change_project", "projects")
        | HasOrganizationPermission("change_project")
        | HasProjectPermission("change_project"),
    ]

    def get_queryset(self):
        return self.project.modules_by_user(self.request.user).linked_projects()

    def check_linked_project_permission(self, project):
        if not self.request.user.can_see_project(project):
            raise LinkedProjectPermissionDeniedError(project.title)

    @transaction.atomic
    def perform_create(self, serializer):
        project = serializer.validated_data["project"]
        self.check_linked_project_permission(project)
        super().perform_create(serializer)

    @transaction.atomic
    def perform_update(self, serializer):
        project = serializer.validated_data.get("project")
        if project:
            self.check_linked_project_permission(project)
        super().perform_update(serializer)

    @extend_schema(
        request=LinkedProjectSerializer(many=True), responses=ProjectSerializer
    )
    @action(
        detail=False,
        methods=["POST"],
        url_name="add-many",
        url_path="add-many",
        permission_classes=[
            IsAuthenticated,
            ProjectIsNotLocked,
            HasBasePermission("change_project", "projects")
            | HasOrganizationPermission("change_project")
            | HasProjectPermission("change_project"),
        ],
    )
    def add_many(self, request, *args, **kwargs):
        """Link projects to a given project."""
        serializer = LinkedProjectSerializer(
            data=request.data, many=True, context={"validate_unique": False}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save(validate=False)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )

    @extend_schema(
        request=ProjectRemoveLinkedProjectSerializer,
        responses=ProjectSerializer,
        parameters=[
            OpenApiParameter(
                "id",
                location=OpenApiParameter.PATH,
                description="ID of the project you want to unlink projects from.",
            )
        ],
    )
    @action(
        detail=False,
        methods=["DELETE"],
        url_name="delete-many",
        url_path="delete-many",
        permission_classes=[
            IsAuthenticated,
            ProjectIsNotLocked,
            HasBasePermission("change_project", "projects")
            | HasOrganizationPermission("change_project")
            | HasProjectPermission("change_project"),
        ],
    )
    def delete_many(self, request, *args, **kwargs):
        """Unlink projects from another projects."""
        project = self.project
        serializer = ProjectRemoveLinkedProjectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        to_unlink = serializer.validated_data["linked_projects"]
        LinkedProject.objects.filter(project__in=to_unlink, target=project).delete()

        context = {"request": request}
        return Response(
            ProjectSerializer(project, context=context).data,
            status=status.HTTP_200_OK,
        )


class ProjectMessageViewSet(NestedProjectViewMixins, viewsets.ModelViewSet):
    serializer_class = ProjectMessageSerializer
    lookup_field = "id"
    lookup_value_regex = "[0-9]+"

    def get_permissions(self):
        codename = map_action_to_permission(self.action, "projectmessage")
        if codename:
            self.permission_classes = [
                IsAuthenticated,
                IsOwner
                | HasBasePermission(codename, "projects")
                | HasOrganizationPermission(codename)
                | HasProjectPermission(codename),
            ]
        return super().get_permissions()

    def get_queryset(self):
        # get_project_related_queryset is not needed because the publication_status is not checked here

        queryset = self.project.modules_by_user(self.request.user).messages()

        if self.action in ["retrieve", "list"]:
            queryset = queryset.exclude(reply_on__isnull=False)

        return queryset.select_related("author").prefetch_related("replies", "images")

    def perform_create(self, serializer):
        message = serializer.save(author=self.request.user, project_id=self.project.id)
        notify_new_private_message.delay(message.id)

    def perform_destroy(self, instance: ProjectMessage):
        instance.soft_delete()


class ProjectMessageImagesView(NestedProjectViewMixins, ImageStorageView):

    def get_permissions(self):
        codename = map_action_to_permission(self.action, "projectmessage")
        if codename:
            self.permission_classes = [
                IsAuthenticated,
                IsOwner
                | HasBasePermission(codename, "projects")
                | HasOrganizationPermission(codename)
                | HasProjectPermission(codename),
            ]
        return super().get_permissions()

    def get_queryset(self):
        messages_qs = self.project.modules_by_user(self.request.user).messages()

        qs = Image.objects.filter(project_messages__in=messages_qs)
        # Retrieve images before message is posted
        if self.request.user.is_authenticated:
            qs = qs | Image.objects.filter(owner=self.request.user)
        return qs.distinct()

    @staticmethod
    def upload_to(instance, filename) -> str:
        return f"project_messages/images/{uuid.uuid4()}#{instance.name}"

    def retrieve(self, request, *args, **kwargs):
        image = self.get_object()
        return redirect(image.file.url)

    def add_image_to_model(self, image, *args, **kwargs):
        return f"/v1/project/{self.project.id}/project-message-image/{image.id}"


class ProjectTabViewset(NestedProjectViewMixins, viewsets.ModelViewSet):
    """Project tabs."""

    serializer_class = ProjectTabSerializer
    filter_backends = [DjangoFilterBackend]
    lookup_field = "id"
    lookup_value_regex = "[^/]+"
    permission_classes = [
        IsAuthenticatedOrReadOnly,
        ProjectIsNotLocked,
        ReadOnly
        | HasBasePermission("change_project", "projects")
        | HasOrganizationPermission("change_project")
        | HasProjectPermission("change_project"),
    ]

    def get_queryset(self) -> QuerySet[ProjectTab]:
        return self.project.modules_by_user(self.request.user).tabs()

    def perform_create(self, serializer: ProjectTabSerializer):
        serializer.save(project=self.project)


class ProjectTabImagesView(NestedProjectViewMixins, ImageStorageView):
    permission_classes = [
        IsAuthenticatedOrReadOnly,
        ProjectIsNotLocked,
        ReadOnly
        | IsOwner
        | HasBasePermission("change_project", "projects")
        | HasOrganizationPermission("change_project")
        | HasProjectPermission("change_project"),
    ]

    def get_queryset(self):
        tabs_qs = self.project.modules_by_user(self.request.user).tabs()

        qs = Image.objects.filter(project_tabs__in=tabs_qs)
        # Retrieve images before tab is posted
        if self.request.user.is_authenticated:
            qs = qs | Image.objects.filter(owner=self.request.user)
        return qs.distinct()

    @staticmethod
    def upload_to(instance, filename) -> str:
        return f"project_tabs/images/{uuid.uuid4()}#{instance.name}"

    def retrieve(self, request, *args, **kwargs):
        image = self.get_object()
        return redirect(image.file.url)

    def add_image_to_model(self, image, *args, **kwargs):
        if "tab_id" in self.request.query_params:
            project_tab = ProjectTab.objects.get(
                project=self.project,
                id=self.request.query_params["tab_id"],
            )
            project_tab.images.add(image)
            project_tab.save()
        return f"/v1/project/{self.project.id}/tab-image/{image.id}"


class ProjectTabItemViewset(
    NestedProjectViewMixins, NestedProjectTabViewMixins, viewsets.ModelViewSet
):
    """Project tabs."""

    serializer_class = ProjectTabItemSerializer
    filter_backends = [DjangoFilterBackend]
    lookup_field = "id"
    lookup_value_regex = "[^/]+"
    permission_classes = [
        IsAuthenticatedOrReadOnly,
        ProjectIsNotLocked,
        ReadOnly
        | HasBasePermission("change_project", "projects")
        | HasOrganizationPermission("change_project")
        | HasProjectPermission("change_project"),
    ]

    def get_queryset(self) -> QuerySet[ProjectTabItem]:
        return self.tab.items.all()

    def perform_create(self, serializer: ProjectTabItemSerializer):
        serializer.save(tab=self.tab)


class ProjectTabItemImagesView(
    NestedProjectViewMixins, NestedProjectTabViewMixins, ImageStorageView
):
    permission_classes = [
        IsAuthenticatedOrReadOnly,
        ProjectIsNotLocked,
        ReadOnly
        | IsOwner
        | HasBasePermission("change_project", "projects")
        | HasOrganizationPermission("change_project")
        | HasProjectPermission("change_project"),
    ]
    multiple_lookup_fields = [(Project, "project_id")]

    def get_queryset(self):
        if "project_id" in self.kwargs and "tab_id" in self.kwargs:
            qs = self.request.user.get_project_related_queryset(
                Image.objects.filter(
                    project_tab_items__tab__project=self.kwargs["project_id"],
                    project_tab_items__tab=self.kwargs["tab_id"],
                ),
                project_related_name="project_tab_items__tab__project",
            )
            # Retrieve images before tab is posted
            if self.request.user.is_authenticated:
                qs = qs | Image.objects.filter(owner=self.request.user)
            return qs.distinct()
        return Image.objects.none()

    @staticmethod
    def upload_to(instance, filename) -> str:
        return f"project_tab_items/images/{uuid.uuid4()}#{instance.name}"

    def retrieve(self, request, *args, **kwargs):
        image = self.get_object()
        return redirect(image.file.url)

    def add_image_to_model(self, image, *args, **kwargs):
        if "project_id" in self.kwargs and "tab_id" in self.kwargs:
            if "tab_item_id" in self.request.query_params:
                tab_item = ProjectTabItem.objects.get(
                    tab__project_id=self.kwargs["project_id"],
                    tab_id=self.kwargs["tab_id"],
                    id=self.request.query_params["tab_item_id"],
                )
                tab_item.images.add(image)
                tab_item.save()
            return f"/v1/project/{self.kwargs['project_id']}/tab/{self.kwargs['tab_id']}/item-image/{image.id}"
        return None
