import uuid

from django.conf import settings
from django.shortcuts import get_object_or_404, redirect
from django.utils.decorators import method_decorator
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from apps.accounts.permissions import HasBasePermission, ReadOnly
from apps.accounts.serializers import UserSerializer
from apps.commons.permissions import IsOwner
from apps.commons.utils.cache import clear_cache_with_key, redis_cache_view
from apps.commons.utils.permissions import map_action_to_permission
from apps.files.models import Image
from apps.files.views import ImageStorageView
from apps.organizations.filters import OrganizationFilter, ProjectCategoryFilter
from apps.organizations.models import Faq, Organization, ProjectCategory
from apps.organizations.permissions import HasOrganizationPermission
from apps.organizations.serializers import (
    FaqSerializer,
    OrganizationAddTeamMembersSerializer,
    OrganizationLightSerializer,
    OrganizationRemoveTeamMembersSerializer,
    OrganizationSerializer,
    ProjectCategorySerializer,
)


class ProjectCategoryViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectCategorySerializer
    filterset_class = ProjectCategoryFilter
    organization_code_lookup = "organization__code"
    queryset = ProjectCategory.objects.select_related(
        "organization", "template"
    ).prefetch_related("wikipedia_tags")
    lookup_field = "id"
    lookup_value_regex = "[0-9]+"

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


class ProjectCategoryBackgroundView(ImageStorageView):
    permission_classes = [
        IsAuthenticatedOrReadOnly,
        ReadOnly
        | IsOwner
        | HasBasePermission("change_projectcategory", "organizations")
        | HasOrganizationPermission("change_projectcategory"),
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


class FaqImagesView(ImageStorageView):
    permission_classes = [
        IsAuthenticatedOrReadOnly,
        ReadOnly
        | HasBasePermission("change_faq", "organizations")
        | HasOrganizationPermission("change_faq"),
    ]

    def get_queryset(self):
        if "organization_code" in self.kwargs:
            qs = Image.objects.filter(
                faqs__organization__code=self.kwargs["organization_code"]
            )
            # Retrieve images before the faq is posted
            return (qs | Image.objects.filter(owner=self.request.user)).distinct()
        return Image.objects.none()

    @staticmethod
    def upload_to(instance, filename) -> str:
        return f"faq/images/{uuid.uuid4()}#{instance.name}"

    def retrieve(self, request, *args, **kwargs):
        image = self.get_object()
        return redirect(image.file.url)

    def add_image_to_model(self, image, *args, **kwargs):
        if "organization_code" in self.kwargs:
            return f"/v1/organization/{self.kwargs['organization_code']}/faq-image/{image.id}"
        return None


class OrganizationViewSet(viewsets.ModelViewSet):
    serializer_class = OrganizationSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = OrganizationFilter
    organization_code_lookup = "code"
    queryset = Organization.objects.select_related(
        "faq", "parent", "banner_image", "logo_image"
    ).prefetch_related("wikipedia_tags")
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
        permission_classes=[ReadOnly],
    )
    def get_people_groups_hierarchy(self, request, *args, **kwargs):
        """Get the people groups hierarchy of the organization."""
        organization = self.get_object()
        root_group = organization.get_or_create_root_people_group()
        return Response(root_group.get_hierarchy(), status=status.HTTP_200_OK)


class FaqViewSet(viewsets.ModelViewSet):
    serializer_class = FaqSerializer
    lookup_field = "id"
    lookup_value_regex = "[0-9]+"

    def get_permissions(self):
        codename = map_action_to_permission(self.action, "faq")
        if codename:
            self.permission_classes = [
                IsAuthenticatedOrReadOnly,
                ReadOnly
                | HasBasePermission(codename, "organizations")
                | HasOrganizationPermission(codename),
            ]
        return super().get_permissions()

    def get_queryset(self):
        if "organization_code" in self.kwargs:
            return Faq.objects.filter(
                organization__code=self.kwargs["organization_code"]
            ).prefetch_related("images")
        return Faq.objects.none()

    def get_object(self):
        """
        Retrieve the object within the QuerySet.

        There should be only one Faq in the QuerySet since we filter by
        `organization_code` in `get_queryset` and there is a one to one relation
        between the objects.
        """
        queryset = self.filter_queryset(self.get_queryset())
        # No need to give additional filters since there should be only one
        # object in the QuerySet
        obj = get_object_or_404(queryset)
        # May raise a permission denied
        self.check_object_permissions(self.request, obj)
        return obj

    def perform_create(self, serializer):
        organization = serializer.validated_data["organization"]
        organization.faq = serializer.save()
        organization.save()


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
            return (qs | Image.objects.filter(owner=self.request.user)).distinct()
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


class TemplateImagesView(ImageStorageView):
    permission_classes = [
        IsAuthenticatedOrReadOnly,
        ReadOnly
        | IsOwner
        | HasBasePermission("change_projectcategory", "organizations")
        | HasOrganizationPermission("change_projectcategory"),
    ]

    def get_queryset(self):
        if "category_id" in self.kwargs:
            qs = Image.objects.filter(
                templates__project_category__id=self.kwargs["category_id"]
            )
            # Retrieve images before the template is posted
            if self.request.user.is_authenticated:
                qs = (qs | Image.objects.filter(owner=self.request.user)).distinct()
            return qs
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
