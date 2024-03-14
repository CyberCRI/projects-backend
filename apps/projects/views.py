import enum
import uuid
from typing import Dict

from django.apps import apps
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.db.models import Prefetch, Q, QuerySet
from django.shortcuts import get_object_or_404, redirect
from django.utils.decorators import method_decorator
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from simple_history.utils import update_change_reason

from apps.accounts.permissions import HasBasePermission
from apps.analytics.models import Stat
from apps.commons.cache import clear_cache_with_key, redis_cache_view
from apps.commons.permissions import IsOwner, ReadOnly
from apps.commons.utils import map_action_to_permission
from apps.commons.views import ListViewSet, MultipleIDViewsetMixin
from apps.files.models import Image
from apps.files.views import ImageStorageView
from apps.notifications.tasks import (
    notify_group_as_member_added,
    notify_group_member_deleted,
    notify_member_added,
    notify_member_deleted,
    notify_member_updated,
    notify_new_blogentry,
    notify_ready_for_review,
)
from apps.organizations.models import Organization
from apps.organizations.permissions import HasOrganizationPermission
from apps.organizations.utils import get_hierarchy_codes
from apps.projects.exceptions import (
    LinkedProjectPermissionDeniedError,
    OrganizationsParameterMissing,
)
from services.mistral.models import ProjectEmbedding

from .filters import LocationFilter, ProjectFilter
from .models import BlogEntry, LinkedProject, Location, Project
from .permissions import HasProjectPermission, ProjectIsNotLocked
from .recommendations import top_project
from .serializers import (
    BlogEntrySerializer,
    LinkedProjectSerializer,
    LocationSerializer,
    ProjectAddLinkedProjectSerializer,
    ProjectAddTeamMembersSerializer,
    ProjectLightSerializer,
    ProjectRemoveLinkedProjectSerializer,
    ProjectRemoveTeamMembersSerializer,
    ProjectSerializer,
    ProjectVersionListSerializer,
    ProjectVersionSerializer,
    TopProjectSerializer,
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
    multiple_lookup_fields = [
        (Project, "id"),
    ]

    def get_permissions(self):
        codename = map_action_to_permission(self.action, "project")
        if codename:
            self.permission_classes = [
                IsAuthenticatedOrReadOnly,
                ProjectIsNotLocked
                | HasBasePermission("change_locked_project", "projects")
                | HasOrganizationPermission("change_locked_project")
                | HasProjectPermission("change_locked_project"),
                ReadOnly
                | HasBasePermission(codename, "projects")
                | HasOrganizationPermission(codename)
                | HasProjectPermission(codename),
            ]
        return super().get_permissions()

    def get_queryset(self) -> QuerySet:
        """Prefetch related models"""
        organizations = Prefetch(
            "organizations",
            queryset=Organization.objects.select_related(
                "faq", "parent", "banner_image", "logo_image"
            ).prefetch_related("wikipedia_tags"),
        )
        return self.request.user.get_project_queryset(
            "wikipedia_tags",
            "goals",
            "follows",
            "follows",
            "reviews",
            "locations",
            "announcements",
            "links",
            "files",
            "images",
            "blog_entries",
            "linked_projects",
            "categories",
            organizations,
        )

    def get_serializer_class(self):
        is_summary = (
            self.request.query_params.get("info_details", None)
            == ProjectViewSet.InfoDetails.SUMMARY
        )
        if self.action == "list" or is_summary:
            return ProjectLightSerializer
        return self.serializer_class

    def get_serializer_context(self):
        """Adds request to the serializer's context."""
        return {"request": self.request}

    @transaction.atomic
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
        update_change_reason(project, f"Updated: {' + '.join(changes.keys())}"[:100])
        if (
            settings.ENABLE_CACHE
            and changes.get("publication_status", None)
            and project.announcements.exists()
        ):
            cache.delete_many(cache.keys("announcements_list_cache*"))
        if changes.get("life_status", "") == Project.LifeStatus.TO_REVIEW:
            notify_ready_for_review.delay(project.pk, self.request.user.pk)
        return project

    def perform_destroy(self, instance):
        if settings.ENABLE_CACHE and instance.announcements.exists():
            cache.delete_many(cache.keys("announcements_list_cache*"))
        super(ProjectViewSet, self).perform_destroy(instance)

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
        return super(ProjectViewSet, self).list(request, *args, **kwargs)

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

        # Collecting many to many items
        organizations = list(project.organizations.all().values_list("id", flat=True))
        categories = list(project.categories.all().values_list("id", flat=True))

        # collecting sub items
        blog_entries = list(project.blog_entries.all())
        goals = list(project.goals.all())
        links = list(project.links.all())
        files = list(project.files.all())
        announcements = list(project.announcements.all())
        locations = list(project.locations.all())
        images = list(project.images.all())
        # keep initial project pk to replace it in description and blog entries
        initial_project_pk = str(project.pk)
        initial_project_slug = project.slug
        # saving a new project in db
        project.pk = None
        project.slug = ""
        project.save()
        # duplicating sub items
        foreign_keys = goals + links + files + announcements + locations
        for item in foreign_keys:
            created_at = getattr(item, "created_at", None)
            item.pk = None
            item.project = project
            item.save()
            if created_at:
                item.created_at = created_at
                item.save(update_fields=["created_at"])

        # duplicating mtm items
        project.organizations.add(*organizations)
        project.categories.add(*categories)
        # header image
        if project.header_image:
            header = project.header_image
            header.pk = None
            header.save()
            header.project_header.set([project])
        # images
        for image in images:
            initial_image_pk = str(image.pk)
            image.pk = None
            image.save()
            image.projects.set([project])
            for identifier in [initial_project_pk, initial_project_slug]:
                project.description = project.description.replace(
                    f"/v1/project/{identifier}/image/{initial_image_pk}/",
                    f"/v1/project/{project.pk}/image/{image.pk}/",
                )
        for blog_entry in blog_entries:
            created_at = getattr(blog_entry, "created_at", None)
            images = list(blog_entry.images.all())
            blog_entry.pk = None
            blog_entry.project = project
            blog_entry.save()
            if created_at:
                blog_entry.created_at = created_at
                blog_entry.save(update_fields=["created_at"])
            for image in images:
                initial_image_pk = str(image.pk)
                image.pk = None
                image.save()
                image.blog_entries.set([blog_entry])
                for identifier in [initial_project_pk, initial_project_slug]:
                    blog_entry.content = blog_entry.content.replace(
                        f"/v1/project/{identifier}/blog-entry-image/{initial_image_pk}/",
                        f"/v1/project/{project.pk}/blog-entry-image/{image.pk}/",
                    )

        project.save()
        # set project owner
        project.setup_permissions(request.user)
        Stat(project=project).save()
        context = {"request": request}
        return Response(
            ProjectSerializer(project, context=context).data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(request=ProjectAddTeamMembersSerializer, responses=ProjectSerializer)
    @action(
        detail=True,
        methods=["POST"],
        url_path="member/add",
        permission_classes=[
            IsAuthenticated,
            HasBasePermission("change_project", "projects")
            | HasOrganizationPermission("change_project")
            | HasProjectPermission("change_project"),
        ],
    )
    @transaction.atomic
    def add_member(self, request, *args, **kwargs):
        """Add users to the project's group of the given name or add group to project.member_people_groups."""
        project = self.get_object()
        serializer = ProjectAddTeamMembersSerializer(
            data={"project": project.pk, **request.data}
        )
        serializer.is_valid(raise_exception=True)
        instances = serializer.save()
        self.notify_add_members(instances)
        project.refresh_from_db()
        project._change_reason = "Added members"
        project.save()
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
                )

    @extend_schema(
        request=ProjectRemoveTeamMembersSerializer, responses=ProjectSerializer
    )
    @action(
        detail=True,
        methods=["POST"],
        url_path="member/remove",
        permission_classes=[
            IsAuthenticated,
            HasBasePermission("change_project", "projects")
            | HasOrganizationPermission("change_project")
            | HasProjectPermission("change_project"),
        ],
    )
    @transaction.atomic
    def remove_member(self, request, *args, **kwargs):
        """Remove users from the project's group of the given name."""
        project = self.get_object()
        # The following 3 lines are here for backward compatibility
        data = request.data.copy()
        if "user" in data and "users" not in data:
            data = {"users": [data["user"]]}
        serializer = ProjectRemoveTeamMembersSerializer(
            data={"project": project.pk, **data}
        )
        serializer.is_valid(raise_exception=True)
        instances = serializer.save()
        self.notify_remove_members(instances)
        project.refresh_from_db()
        project._change_reason = "Removed members"
        project.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

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

    def notify_remove_members(self, instances):
        for user in instances["users"]:
            notify_member_deleted.delay(
                instances["project"].pk, user.pk, self.request.user.pk
            )
        for people_group in instances["people_groups"]:
            notify_group_member_deleted.delay(
                instances["project"].pk, people_group.pk, self.request.user.pk
            )

    def _toggle_is_locked(self, value):
        project = self.get_object()
        project.is_locked = value
        project.save()
        return Response(status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=["post"],
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
        methods=["post"],
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
        responses=ProjectLightSerializer,
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
                description="Comma-separated list of organization codes.",
                required=False,
                type=str,
            ),
        ],
    )
    @action(
        detail=True,
        methods=["GET"],
        permission_classes=[ReadOnly],
    )
    def similar(self, request, *args, **kwargs):
        project = self.get_object()
        embedding, _ = ProjectEmbedding.objects.get_or_create(item=project)
        vector = embedding.embedding or embedding.vectorize().embedding
        if vector is None:
            return Response([])
        organizations = [
            o for o in request.query_params.get("organizations", "").split(",") if o
        ]
        if not organizations:
            raise OrganizationsParameterMissing
        threshold = int(request.query_params.get("threshold", 5))
        queryset = self.request.user.get_project_queryset().filter(
            organizations__code__in=get_hierarchy_codes(organizations)
        )
        queryset = ProjectEmbedding.vector_search(vector, queryset)[:threshold]
        return Response(ProjectLightSerializer(queryset, many=True).data)


class ProjectTopViewSet(ListViewSet):
    """Allows to retrieve the top projects."""

    permission_classes = [ReadOnly]
    project_scores: Dict[str, float]
    serializer_class = TopProjectSerializer
    filter_backends = [DjangoFilterBackend]

    def get_queryset(self):
        """Return a queryset sorted according to a computed score.

        Additionally, set `self.project_scores` so that it can be added to the
        serializer's context later.
        """
        prefetch_organizations = Prefetch(
            "organizations",
            queryset=Organization.objects.select_related(
                "faq", "parent", "banner_image", "logo_image"
            ).prefetch_related("wikipedia_tags"),
        )
        queryset = self.request.user.get_project_queryset(
            prefetch_organizations, "categories"
        )
        organizations_param = self.request.query_params.get("organizations", None)
        organizations = None
        if organizations_param is not None:
            organizations_param = organizations_param.split(",")
            organizations = Organization.objects.filter(
                Q(code__in=organizations_param)
                | Q(parent__code__in=organizations_param)
            )
            queryset = queryset.filter(
                Q(organizations__in=organizations)
                | Q(organizations__parent__in=organizations)
            )

        queryset, scores = top_project(queryset, organizations)
        self.project_scores = scores
        return queryset.distinct()

    def get_serializer_context(self):
        """Add the request and each project's score to the serializer's context."""
        return {"request": self.request, "scores": self.project_scores}


class RandomProjectViewSet(ListViewSet):
    serializer_class = ProjectLightSerializer
    permission_classes = [ReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_class = ProjectFilter

    def get_queryset(self):
        organizations = Prefetch(
            "organizations",
            queryset=Organization.objects.select_related(
                "faq", "parent", "banner_image", "logo_image"
            ).prefetch_related("wikipedia_tags"),
        )
        qs = self.request.user.get_project_queryset(organizations, "categories")
        return qs.order_by("?")


class ProjectHeaderView(MultipleIDViewsetMixin, ImageStorageView):
    permission_classes = [
        IsAuthenticatedOrReadOnly,
        ReadOnly
        | IsOwner
        | HasBasePermission("change_project", "projects")
        | HasOrganizationPermission("change_project")
        | HasProjectPermission("change_project"),
    ]
    multiple_lookup_fields = [
        (Project, "project_id"),
    ]

    def get_queryset(self):
        if "project_id" in self.kwargs:
            return Image.objects.filter(project_header__id=self.kwargs["project_id"])
        return Image.objects.none()

    @staticmethod
    def upload_to(instance, filename) -> str:
        return f"project/header/{uuid.uuid4()}#{instance.name}"

    def add_image_to_model(self, image):
        if "project_id" in self.kwargs:
            project = Project.objects.get(id=self.kwargs["project_id"])
            project.header_image = image
            project.save()
            return f"/v1/project/{self.kwargs['project_id']}/header/{image.id}"
        return None


class ProjectImagesView(MultipleIDViewsetMixin, ImageStorageView):
    permission_classes = [
        IsAuthenticatedOrReadOnly,
        ReadOnly
        | IsOwner
        | HasBasePermission("change_project", "projects")
        | HasOrganizationPermission("change_project")
        | HasProjectPermission("change_project"),
    ]
    multiple_lookup_fields = [
        (Project, "project_id"),
    ]

    def get_queryset(self):
        if "project_id" in self.kwargs:
            qs = self.request.user.get_project_related_queryset(
                Image.objects.filter(projects=self.kwargs["project_id"]),
                project_related_name="projects",
            )
            # Retrieve images before project is posted
            if self.request.user.is_authenticated:
                qs = (qs | Image.objects.filter(owner=self.request.user)).distinct()
            return qs
        return Image.objects.none()

    @staticmethod
    def upload_to(instance, filename) -> str:
        return f"project/images/{uuid.uuid4()}#{instance.name}"

    def retrieve(self, request, *args, **kwargs):
        image = self.get_object()
        return redirect(image.file.url)

    def add_image_to_model(self, image, *args, **kwargs):
        if "project_id" in self.kwargs:
            project = Project.objects.get(id=self.kwargs["project_id"])
            project.images.add(image)
            project.save()
            return f"/v1/project/{self.kwargs['project_id']}/image/{image.id}"
        return None


class BlogEntryViewSet(MultipleIDViewsetMixin, viewsets.ModelViewSet):
    serializer_class = BlogEntrySerializer
    filter_backends = [DjangoFilterBackend]
    lookup_field = "id"
    lookup_value_regex = "[0-9]+"
    permission_classes = [
        IsAuthenticatedOrReadOnly,
        ReadOnly
        | HasBasePermission("change_project", "projects")
        | HasOrganizationPermission("change_project")
        | HasProjectPermission("change_project"),
    ]
    multiple_lookup_fields = [
        (Project, "project_id"),
    ]

    def get_queryset(self) -> QuerySet:
        if "project_id" in self.kwargs:
            return self.request.user.get_project_related_queryset(
                BlogEntry.objects.filter(project=self.kwargs["project_id"]),
            ).prefetch_related("images")
        return BlogEntry.objects.none()

    def perform_create(self, serializer):
        instance = serializer.save()
        notify_new_blogentry.delay(instance.pk, self.request.user.pk)


class BlogEntryImagesView(MultipleIDViewsetMixin, ImageStorageView):
    permission_classes = [
        IsAuthenticatedOrReadOnly,
        ReadOnly
        | IsOwner
        | HasBasePermission("change_project", "projects")
        | HasOrganizationPermission("change_project")
        | HasProjectPermission("change_project"),
    ]
    multiple_lookup_fields = [
        (Project, "project_id"),
    ]

    def get_queryset(self):
        if "project_id" in self.kwargs:
            qs = self.request.user.get_project_related_queryset(
                Image.objects.filter(blog_entries__project=self.kwargs["project_id"]),
                project_related_name="blog_entries__project",
            )
            # Retrieve images before blog entry is posted
            if self.request.user.is_authenticated:
                qs = (qs | Image.objects.filter(owner=self.request.user)).distinct()
            return qs
        return Image.objects.none()

    @staticmethod
    def upload_to(instance, filename) -> str:
        return f"blog_entry/images/{uuid.uuid4()}#{instance.name}"

    def retrieve(self, request, *args, **kwargs):
        image = self.get_object()
        return redirect(image.file.url)

    def add_image_to_model(self, image, *args, **kwargs):
        if "project_id" in self.kwargs:
            return (
                f"/v1/project/{self.kwargs['project_id']}/blog-entry-image/{image.id}"
            )
        return None


class LocationViewSet(MultipleIDViewsetMixin, viewsets.ModelViewSet):
    serializer_class = LocationSerializer
    lookup_field = "id"
    lookup_value_regex = "[0-9]+"
    pagination_class = None
    permission_classes = [
        IsAuthenticatedOrReadOnly,
        ReadOnly
        | HasBasePermission("change_project", "projects")
        | HasOrganizationPermission("change_project")
        | HasProjectPermission("change_project"),
    ]
    multiple_lookup_fields = [
        (Project, "project_id"),
    ]

    def get_queryset(self):
        qs = self.request.user.get_project_related_queryset(Location.objects)
        if "project_id" in self.kwargs:
            qs = qs.filter(project=self.kwargs["project_id"])
        return qs.select_related("project")

    @method_decorator(
        redis_cache_view("locations_list_cache", settings.CACHE_LOCATIONS_LIST_TTL)
    )
    def list(self, request, *args, **kwargs):
        return super(LocationViewSet, self).list(request, *args, **kwargs)

    @method_decorator(clear_cache_with_key("locations_list_cache"))
    def dispatch(self, request, *args, **kwargs):
        return super(LocationViewSet, self).dispatch(request, *args, **kwargs)


class ReadLocationViewSet(LocationViewSet):
    http_method_names = ["get", "list"]
    filterset_class = LocationFilter


class HistoricalProjectViewSet(MultipleIDViewsetMixin, viewsets.ReadOnlyModelViewSet):
    lookup_field = "pk"
    permission_classes = [ReadOnly]
    multiple_lookup_fields = [
        (Project, "project_id"),
    ]

    def get_serializer_class(self):
        if self.action == "list":
            return ProjectVersionListSerializer
        return ProjectVersionSerializer

    def get_queryset(self) -> QuerySet:
        if "project_id" in self.kwargs:
            project = get_object_or_404(
                self.request.user.get_project_queryset(), id=self.kwargs["project_id"]
            )
            return apps.get_model("projects", "HistoricalProject").objects.filter(
                history_relation=project,
                history_change_reason__isnull=False,
            )
        return apps.get_model("projects", "HistoricalProject").objects.none()


class LinkedProjectViewSet(MultipleIDViewsetMixin, viewsets.ModelViewSet):
    serializer_class = LinkedProjectSerializer
    http_method_names = ["post", "patch", "delete"]
    lookup_field = "id"
    lookup_value_regex = "[0-9]+"
    permission_classes = [
        IsAuthenticatedOrReadOnly,
        ReadOnly
        | HasBasePermission("change_project", "projects")
        | HasOrganizationPermission("change_project")
        | HasProjectPermission("change_project"),
    ]
    multiple_lookup_fields = [
        (Project, "project_id"),
    ]

    def get_queryset(self):
        if "project_id" in self.kwargs:
            qs = self.request.user.get_project_related_queryset(
                LinkedProject.objects.all(), project_related_name="target"
            )
            return qs.filter(target__id=self.kwargs["project_id"])
        return LinkedProject.objects.none()

    def check_linked_project_permission(self, project):
        if not self.request.user.can_see_project(project):
            raise LinkedProjectPermissionDeniedError(project.title)

    @transaction.atomic
    def perform_create(self, serializer):
        project = Project.objects.get(id=self.kwargs["project_id"])
        self.check_linked_project_permission(project)
        super(LinkedProjectViewSet, self).perform_create(serializer)
        project._change_reason = "Added linked projects"
        project.save()

    @transaction.atomic
    def perform_destroy(self, instance):
        project = instance.target
        super(LinkedProjectViewSet, self).perform_destroy(instance)
        project._change_reason = "Removed linked projects"
        project.save()

    @transaction.atomic
    def perform_update(self, serializer):
        project = Project.objects.get(id=self.kwargs["project_id"])
        self.check_linked_project_permission(project)
        super(LinkedProjectViewSet, self).perform_update(serializer)
        project._change_reason = "Updated linked projects"
        project.save()

    @extend_schema(
        request=ProjectAddLinkedProjectSerializer,
        responses=ProjectSerializer,
    )
    @action(
        detail=False,
        methods=["POST"],
        url_name="add-many",
        url_path="add-many",
        permission_classes=[
            IsAuthenticated,
            HasBasePermission("change_project", "projects")
            | HasOrganizationPermission("change_project")
            | HasProjectPermission("change_project"),
        ],
    )
    def add_many(self, request, *args, **kwargs):
        """Link projects to a given project."""
        project = Project.objects.get(id=self.kwargs["project_id"])
        serializer = ProjectAddLinkedProjectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            for p in serializer.validated_data["projects"]:
                # Check the user has permission on all projects to be linked
                self.check_linked_project_permission(p["project"])
                LinkedProject.objects.create(
                    project=p["project"],
                    target=project,
                )
            project._change_reason = "Added linked projects"
            project.save()

        context = {"request": request}
        return Response(
            ProjectSerializer(project, context=context).data,
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
            HasBasePermission("change_project", "projects")
            | HasOrganizationPermission("change_project")
            | HasProjectPermission("change_project"),
        ],
    )
    def delete_many(self, request, *args, **kwargs):
        """Unlink projects from another projects."""
        project = Project.objects.get(id=self.kwargs["project_id"])
        serializer = ProjectRemoveLinkedProjectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        to_unlink = serializer.validated_data["linked_projects"]
        with transaction.atomic():
            LinkedProject.objects.filter(project__in=to_unlink, target=project).delete()
            project._change_reason = "Removed linked projects"
            project.save()

        context = {"request": request}
        return Response(
            ProjectSerializer(project, context=context).data,
            status=status.HTTP_200_OK,
        )
