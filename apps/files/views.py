from abc import abstractmethod
from typing import Any, Callable, Dict

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
from apps.commons.permissions import ReadOnly
from apps.commons.views import MultipleIDViewsetMixin
from apps.organizations.models import Organization
from apps.organizations.permissions import HasOrganizationPermission
from apps.projects.models import Project
from apps.projects.permissions import HasProjectPermission, ProjectIsNotLocked

from .exceptions import ProtectedImageError
from .models import AttachmentFile, AttachmentLink, Image, OrganizationAttachmentFile
from .serializers import (
    AttachmentFileSerializer,
    AttachmentLinkSerializer,
    ImageSerializer,
    OrganizationAttachmentFileSerializer,
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
    permission_classes = [
        IsAuthenticatedOrReadOnly,
        ReadOnly
        | HasBasePermission("", "organizations")
        | HasOrganizationPermission(""),
    ]

    def get_queryset(self) -> QuerySet:
        if "organization_code" in self.kwargs:
            return OrganizationAttachmentFile.filter(
                organization__code=self.kwargs["organization_code"]
            )
        return OrganizationAttachmentFile.objects.none()

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

    def validate_image(self, data: Dict[str, Any]):
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
