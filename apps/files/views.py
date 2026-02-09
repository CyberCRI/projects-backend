from abc import abstractmethod
from collections.abc import Callable
from typing import Any

from django.db import transaction
from django.db.models import QuerySet
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from apps.accounts.permissions import HasBasePermission
from apps.commons.permissions import IsOwner, ReadOnly, WillBeOwner
from apps.commons.utils import map_action_to_permission
from apps.commons.views import MultipleIDViewsetMixin, NestedPeopleGroupViewMixins
from apps.organizations.models import Organization
from apps.organizations.permissions import HasOrganizationPermission
from apps.projects.models import Project
from apps.projects.permissions import HasProjectPermission, ProjectIsNotLocked
from lib.views import NestedOrganizationViewMixins

from .exceptions import ProtectedImageError
from .models import (
    AttachmentFile,
    AttachmentLink,
    Image,
    OrganizationAttachmentFile,
    ProjectUserAttachmentFile,
    ProjectUserAttachmentLink,
)
from .serializers import (
    AttachmentFileSerializer,
    AttachmentLinkSerializer,
    ImageSerializer,
    OrganizationAttachmentFileSerializer,
    PeopleGroupImageSerializer,
    ProjectUserAttachmentFileSerializer,
    ProjectUserAttachmentLinkSerializer,
)


class AttachmentLinkViewSet(MultipleIDViewsetMixin, viewsets.ModelViewSet):
    serializer_class = AttachmentLinkSerializer
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
    multiple_lookup_fields = [
        (Project, "project_id"),
    ]

    def get_queryset(self) -> QuerySet:
        if "project_id" in self.kwargs:
            qs = self.request.user.get_project_related_queryset(
                AttachmentLink.objects.all()
            )
            return qs.filter(project=self.kwargs["project_id"])
        return AttachmentLink.objects.none()


class OrganizationAttachmentFileViewSet(viewsets.ModelViewSet):
    parser_classes = [MultiPartParser]
    serializer_class = OrganizationAttachmentFileSerializer
    filter_backends = [DjangoFilterBackend]
    lookup_field = "id"
    lookup_value_regex = "[0-9]+"

    def get_permissions(self):
        codename = map_action_to_permission(self.action, "organizationattachmentfile")
        if codename:
            self.permission_classes = [
                IsAuthenticatedOrReadOnly,
                ReadOnly
                | HasBasePermission(codename, "organizations")
                | HasOrganizationPermission(codename),
            ]
        return super().get_permissions()

    def get_queryset(self) -> QuerySet:
        if "organization_code" in self.kwargs:
            return OrganizationAttachmentFile.objects.filter(
                organization__code=self.kwargs["organization_code"]
            )
        return OrganizationAttachmentFile.objects.none()

    def get_serializer_context(self):
        return {
            **super().get_serializer_context(),
            "organization_code": self.kwargs.get("organization_code"),
        }

    def perform_create(self, serializer):
        organization = get_object_or_404(
            Organization, code=self.kwargs["organization_code"]
        )
        serializer.save(organization=organization)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        return redirect(instance.file.url)


class AttachmentFileViewSet(MultipleIDViewsetMixin, viewsets.ModelViewSet):
    parser_classes = [MultiPartParser]
    serializer_class = AttachmentFileSerializer
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
    multiple_lookup_fields = [
        (Project, "project_id"),
    ]

    def get_queryset(self) -> QuerySet:
        if "project_id" in self.kwargs:
            qs = self.request.user.get_project_related_queryset(
                AttachmentFile.objects.all()
            )
            return qs.filter(project=self.kwargs["project_id"])
        return AttachmentFile.objects.none()

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        return redirect(instance.file.url)


class ImageStorageView(viewsets.GenericViewSet, mixins.UpdateModelMixin):
    """Allows the upload of images."""

    queryset = Image.objects.all()
    serializer_class = ImageSerializer
    parser_classes = [MultiPartParser]
    permission_classes = [IsAuthenticated]
    upload_to: Callable[[Image, str], str] = None

    def get_upload_to(self) -> Callable[[Image, str], str]:
        """Return a `Callable` that will be used as the `upload_to` function.

        You can override this method instead of defining an `upload_to` function
        if you want to provide different `Callable` depending on the incoming
        request.
        """
        assert self.upload_to is not None, (
            "'%s' should either include a `upload_to` attribute, "
            "or override the `get_upload_to()` method." % self.__class__.__name__
        )

        return self.upload_to

    def validate_image(self, data: dict[str, Any]):
        """Allows to modify the image before saving it.

        For more information about the `ImageFile` object, see:
         * https://docs.djangoproject.com/en/4.0/ref/files/file/#the-file-class
         * https://docs.djangoproject.com/en/4.0/ref/files/file/#the-imagefile-class
        """
        # Check that image is not too large by calling serializer.is_valid()
        ImageSerializer(data=data).is_valid(raise_exception=True)

    @abstractmethod
    def add_image_to_model(self, image):
        """
        After image has been created, we need to add it to the related object.
        """
        return

    def get_relation(self, image: Image) -> dict:
        for relation in Image._meta.related_objects:
            model = relation.related_model
            field_name = relation.field.name
            queryset = model.objects.filter(**{field_name: image})
            if queryset.count() > 0:
                return {
                    "model": model.__name__,
                    "pk": queryset[0].pk,
                    "field": field_name,
                }
        return {"model": None, "pk": None, "field": None}

    @extend_schema(
        parameters=[
            OpenApiParameter("Content-Disposition", location=OpenApiParameter.HEADER)
        ],
        request=OpenApiTypes.BINARY,
        responses={201: ImageSerializer},
    )
    def create(self, request, *args, **kwargs):
        """Allows the upload of images."""
        data = {
            "file": request.data["file"],
            "name": request.data["file"]._name,
            **{k: v for k, v in request.data.items() if k != "file"},
        }
        self.validate_image(data)
        image = Image(**data)
        image._upload_to = self.get_upload_to()
        with transaction.atomic():
            image.owner = request.user
            image.save()
            static_url = self.add_image_to_model(image)
            data = ImageSerializer(image).data
            return Response({"static_url": static_url, **data}, status=201)

    def destroy(self, request, *args, **kwargs):
        image = self.get_object()
        try:
            image.delete()
        except ProtectedError:
            relation = self.get_relation(image)
            raise ProtectedImageError(relation)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProjectUserAttachmentLinkViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectUserAttachmentLinkSerializer
    lookup_field = "id"
    lookup_value_regex = "[0-9]+"
    permission_classes = [
        ReadOnly
        | IsOwner
        | WillBeOwner
        | HasBasePermission("change_projectuser", "accounts")
        | HasOrganizationPermission("change_projectuser"),
    ]

    def get_queryset(self) -> QuerySet:
        return ProjectUserAttachmentLink.objects.filter(
            owner__pk=self.kwargs["user_id"]
        )

    def create(self, request, *ar, **kw):
        request.data["owner"] = int(self.kwargs["user_id"])
        return super().create(request, *ar, **kw)


class ProjectUserAttachmentFileViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectUserAttachmentFileSerializer
    lookup_field = "id"
    lookup_value_regex = "[0-9]+"
    permission_classes = [
        ReadOnly
        | IsOwner
        | WillBeOwner
        | HasBasePermission("change_projectuser", "accounts")
        | HasOrganizationPermission("change_projectuser"),
    ]

    def get_queryset(self) -> QuerySet:
        return ProjectUserAttachmentFile.objects.filter(
            owner__pk=self.kwargs["user_id"]
        )

    @extend_schema(
        parameters=[
            OpenApiParameter("Content-Disposition", location=OpenApiParameter.HEADER)
        ],
        request=OpenApiTypes.BINARY,
        responses={201: ProjectUserAttachmentFileSerializer},
    )
    def create(self, request, *ar, **kw):
        request.data["owner"] = int(self.kwargs["user_id"])
        return super().create(request, *ar, **kw)


class PeopleGroupGalleryViewSet(
    NestedOrganizationViewMixins, NestedPeopleGroupViewMixins, viewsets.ModelViewSet
):
    serializer_class = PeopleGroupImageSerializer

    def get_queryset(self):
        modules_manager = self.people_group.get_related_module()
        modules = modules_manager(self.people_group, self.request.user)
        return modules.gallery()

    def create(self, request, *ar, **kw):
        request.data["people_group"] = self.people_group.id
        return super().create(request, *ar, **kw)
