import uuid

from django.conf import settings
from django.db import transaction
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from apps.accounts.models import PeopleGroup
from apps.accounts.permissions import HasBasePermission
from apps.accounts.serializers import UserSerializer
from apps.commons.cache import clear_cache_with_key, redis_cache_view
from apps.commons.permissions import IsOwner, ReadOnly
from apps.commons.utils import map_action_to_permission
from apps.commons.views import MultipleIDViewsetMixin
from apps.files.models import Image
from apps.files.views import ImageStorageView
from apps.organizations.filters import OrganizationFilter, ProjectCategoryFilter
from apps.organizations.models import Organization, ProjectCategory
from apps.organizations.permissions import HasOrganizationPermission
from apps.organizations.serializers import (
    OrganizationAddFeaturedProjectsSerializer,
    OrganizationAddTeamMembersSerializer,
    OrganizationLightSerializer,
    OrganizationRemoveFeaturedProjectsSerializer,
    OrganizationRemoveTeamMembersSerializer,
    OrganizationSerializer,
    ProjectCategorySerializer,
)
from apps.projects.serializers import ProjectLightSerializer


class ProjectCategoryViewSet(MultipleIDViewsetMixin, viewsets.ModelViewSet):
    serializer_class = ProjectCategorySerializer
    filterset_class = ProjectCategoryFilter
    organization_code_lookup = "organization__code"
    lookup_field = "id"
    lookup_value_regex = "[^/]+"
    multiple_lookup_fields = [
        (ProjectCategory, "id"),
    ]

    def get_queryset(self):
        return (
            ProjectCategory.objects.filter(is_root=False)
            .select_related("organization")
            .prefetch_related("tags")
        )

    def get_permissions(self):
        codename = map_action_to_permission(self.action, "projectcategory")
        if codename:
            self.permission_classes = [
                IsAuthenticatedOrReadOnly,
                ReadOnly
                | HasBasePermission(codename, "organizations")
                | HasOrganizationPermission(codename),
            ]
        return super().get_permissions()

    @method_decorator(
        redis_cache_view("categories_list_cache", settings.CACHE_CATEGORIES_LIST_TTL)
    )
    def list(self, request, *args, **kwargs):
        return super(ProjectCategoryViewSet, self).list(request, *args, **kwargs)

    @method_decorator(clear_cache_with_key("categories_list_cache"))
    def dispatch(self, request, *args, **kwargs):
        return super(ProjectCategoryViewSet, self).dispatch(request, *args, **kwargs)

    @action(
        detail=True,
        methods=["GET"],
        url_path="hierarchy",
        permission_classes=[ReadOnly],
    )
    def hierarchy(self, request, *args, **kwargs):
        project_category = self.get_object()
        return Response(project_category.get_hierarchy(), status=status.HTTP_200_OK)


class ProjectCategoryBackgroundView(MultipleIDViewsetMixin, ImageStorageView):
    permission_classes = [
        IsAuthenticatedOrReadOnly,
        ReadOnly
        | IsOwner
        | HasBasePermission("change_projectcategory", "organizations")
        | HasOrganizationPermission("change_projectcategory"),
    ]
    multiple_lookup_fields = [
        (ProjectCategory, "category_id"),
    ]

    def get_queryset(self):
        if "category_id" in self.kwargs:
            return Image.objects.filter(project_category__id=self.kwargs["category_id"])
        return Image.objects.none()

    @staticmethod
    def upload_to(instance, filename) -> str:
        return f"category/background/{uuid.uuid4()}#{instance.name}"

    def add_image_to_model(self, image):
        if "category_id" in self.kwargs:
            category = ProjectCategory.objects.get(id=self.kwargs["category_id"])
            category.background_image = image
            category.save()
            return f"/v1/category/{self.kwargs['category_id']}/background/{image.id}"
        return None


class OrganizationViewSet(viewsets.ModelViewSet):
    serializer_class = OrganizationSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = OrganizationFilter
    organization_code_lookup = "code"
    queryset = Organization.objects.all()
    lookup_field = "code"
    lookup_value_regex = "[a-zA-Z0-9_-]+"

    def get_permissions(self):
        codename = map_action_to_permission(self.action, "organization")
        if codename:
            self.permission_classes = [
                IsAuthenticatedOrReadOnly,
                ReadOnly
                | HasBasePermission(codename, "organizations")
                | HasOrganizationPermission(codename),
            ]
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action == "list":
            return OrganizationLightSerializer
        return self.serializer_class

    @method_decorator(
        redis_cache_view(
            "organizations_list_cache", settings.CACHE_ORGANIZATIONS_LIST_TTL
        )
    )
    def list(self, request, *args, **kwargs):
        return super(OrganizationViewSet, self).list(request, *args, **kwargs)

    @method_decorator(clear_cache_with_key("organizations_list_cache"))
    def dispatch(self, request, *args, **kwargs):
        return super(OrganizationViewSet, self).dispatch(request, *args, **kwargs)

    @extend_schema(
        request=OrganizationAddTeamMembersSerializer, responses=UserSerializer
    )
    @action(
        detail=True,
        methods=["POST"],
        url_path="member/add",
        permission_classes=[
            IsAuthenticated,
            HasBasePermission("change_organization", "organizations")
            | HasOrganizationPermission("change_organization"),
        ],
    )
    def add_member(self, request, *args, **kwargs):
        """Add users to the organization's group of the given name."""
        organization = self.get_object()
        serializer = OrganizationAddTeamMembersSerializer(
            data={"organization": organization.pk, **request.data}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        request=OrganizationRemoveTeamMembersSerializer, responses=UserSerializer
    )
    @action(
        detail=True,
        methods=["POST"],
        url_path="member/remove",
        permission_classes=[
            IsAuthenticated,
            HasBasePermission("change_organization", "organizations")
            | HasOrganizationPermission("change_organization"),
        ],
    )
    def remove_member(self, request, *args, **kwargs):
        """Remove users from the organization's group of the given name."""
        organization = self.get_object()
        serializer = OrganizationRemoveTeamMembersSerializer(
            data={"organization": organization.pk, **request.data}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=["GET"],
        url_path="people-groups-hierarchy",
        url_name="people-groups-hierarchy",
        permission_classes=[ReadOnly],
    )
    def get_people_groups_hierarchy(self, request, *args, **kwargs):
        """Get the people groups hierarchy of the organization."""
        organization = self.get_object()
        root_group = PeopleGroup.update_or_create_root(organization)
        return Response(
            root_group.get_hierarchy(self.request.user), status=status.HTTP_200_OK
        )

    @action(
        detail=True,
        methods=["GET"],
        url_path="categories-hierarchy",
        url_name="categories-hierarchy",
        permission_classes=[ReadOnly],
    )
    def get_project_categories_hierarchy(self, request, *args, **kwargs):
        """Get the people groups hierarchy of the organization."""
        organization = self.get_object()
        root_group = ProjectCategory.update_or_create_root(organization)
        return Response(root_group.get_hierarchy(), status=status.HTTP_200_OK)

    @extend_schema(
        request=OrganizationAddFeaturedProjectsSerializer,
        responses=OrganizationSerializer,
    )
    @action(
        detail=True,
        methods=["POST"],
        url_path="featured-project/add",
        permission_classes=[
            IsAuthenticated,
            HasBasePermission("change_organization", "organizations")
            | HasOrganizationPermission("change_organization"),
        ],
    )
    @transaction.atomic
    def add_featured_project(self, request, *args, **kwargs):
        organization = self.get_object()
        serializer = OrganizationAddFeaturedProjectsSerializer(
            data={"organization": organization.pk, **request.data},
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        request=OrganizationRemoveFeaturedProjectsSerializer,
        responses=OrganizationSerializer,
    )
    @action(
        detail=True,
        methods=["POST"],
        url_path="featured-project/remove",
        permission_classes=[
            IsAuthenticated,
            HasBasePermission("change_organization", "organizations")
            | HasOrganizationPermission("change_organization"),
        ],
    )
    def remove_featured_project(self, request, *args, **kwargs):
        organization = self.get_object()
        serializer = OrganizationRemoveFeaturedProjectsSerializer(
            data={"organization": organization.pk, **request.data}
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
        url_path="featured-project",
        permission_classes=[ReadOnly],
    )
    def featured_project(self, request, *args, **kwargs):
        organization = self.get_object()
        queryset = (
            self.request.user.get_project_queryset()
            .filter(org_featured_projects=organization)
            .distinct()
            .prefetch_related("categories")
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


class OrganizationBannerView(ImageStorageView):
    permission_classes = [
        IsAuthenticatedOrReadOnly,
        ReadOnly
        | IsOwner
        | HasBasePermission("change_organization", "organizations")
        | HasOrganizationPermission("change_organization"),
    ]

    def get_queryset(self):
        if "organization_code" in self.kwargs:
            return Image.objects.filter(
                organization_banner__code=self.kwargs["organization_code"]
            )
        return Image.objects.none()

    @staticmethod
    def upload_to(instance, filename) -> str:
        return f"organization/banner/{uuid.uuid4()}#{instance.name}"

    def add_image_to_model(self, image):
        if "organization_code" in self.kwargs:
            organization = Organization.objects.get(
                code=self.kwargs["organization_code"]
            )
            organization.banner_image = image
            organization.save()
            return (
                f"/v1/organization/{self.kwargs['organization_code']}/banner/{image.id}"
            )
        return None


class OrganizationLogoView(ImageStorageView):
    permission_classes = [
        IsAuthenticatedOrReadOnly,
        ReadOnly
        | IsOwner
        | HasBasePermission("change_organization", "organizations")
        | HasOrganizationPermission("change_organization"),
    ]

    def get_queryset(self):
        if "organization_code" in self.kwargs:
            return Image.objects.filter(
                organization_logo__code=self.kwargs["organization_code"]
            )
        return Image.objects.none()

    def retrieve(self, request, *args, **kwargs):
        image = self.get_object()
        return redirect(image.file.url)

    @staticmethod
    def upload_to(instance, filename) -> str:
        return f"organization/logo/{uuid.uuid4()}#{instance.name}"

    def add_image_to_model(self, image):
        if "organization_code" in self.kwargs:
            organization = Organization.objects.get(
                code=self.kwargs["organization_code"]
            )
            organization.logo_image = image
            organization.save()
            return (
                f"/v1/organization/{self.kwargs['organization_code']}/logo/{image.id}"
            )
        return None


class OrganizationImagesView(ImageStorageView):
    permission_classes = [
        IsAuthenticatedOrReadOnly,
        ReadOnly
        | IsOwner
        | HasBasePermission("change_organization", "organizations")
        | HasOrganizationPermission("change_organization"),
    ]

    def get_queryset(self):
        if "organization_code" in self.kwargs:
            qs = Image.objects.filter(
                organizations__code=self.kwargs["organization_code"]
            )
            # Retrieve images before the organization is posted
            if self.request.user.is_authenticated:
                qs = qs | Image.objects.filter(owner=self.request.user)
            return qs.distinct()
        return Image.objects.none()

    def retrieve(self, request, *args, **kwargs):
        image = self.get_object()
        return redirect(image.file.url)

    @staticmethod
    def upload_to(instance, filename) -> str:
        return f"organization/images/{uuid.uuid4()}#{instance.name}"

    def add_image_to_model(self, image):
        if "organization_code" in self.kwargs:
            organization = Organization.objects.get(
                code=self.kwargs["organization_code"]
            )
            organization.images.add(image)
            organization.save()
            return (
                f"/v1/organization/{self.kwargs['organization_code']}/image/{image.id}"
            )
        return None


class TemplateImagesView(MultipleIDViewsetMixin, ImageStorageView):
    permission_classes = [
        IsAuthenticatedOrReadOnly,
        ReadOnly
        | IsOwner
        | HasBasePermission("change_projectcategory", "organizations")
        | HasOrganizationPermission("change_projectcategory"),
    ]
    multiple_lookup_fields = [
        (ProjectCategory, "category_id"),
    ]

    def get_queryset(self):
        if "category_id" in self.kwargs:
            qs = Image.objects.filter(
                templates__project_category__id=self.kwargs["category_id"]
            )
            # Retrieve images before the template is posted
            if self.request.user.is_authenticated:
                qs = qs | Image.objects.filter(owner=self.request.user)
            return qs.distinct()
        return Image.objects.none()

    @staticmethod
    def upload_to(instance, filename) -> str:
        return f"template/images/{uuid.uuid4()}#{instance.name}"

    def retrieve(self, request, *args, **kwargs):
        image = self.get_object()
        return redirect(image.file.url)

    def add_image_to_model(self, image, *args, **kwargs):
        if "category_id" in self.kwargs:
            return (
                f"/v1/category/{self.kwargs['category_id']}/template-image/{image.id}"
            )
        return None
