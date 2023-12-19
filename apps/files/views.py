from abc import abstractmethod
from typing import Callable

from django.core.files import File
from django.core.files.images import ImageFile
from django.db import transaction
from django.db.models import QuerySet
from django.db.models.deletion import ProtectedError
from django.shortcuts import redirect
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from apps.accounts.permissions import HasBasePermission, ReadOnly
from apps.organizations.permissions import HasOrganizationPermission
from apps.projects.models import Project
from apps.projects.permissions import HasProjectPermission

from .models import AttachmentFile, AttachmentLink, Image
from .serializers import (
    AttachmentFileSerializer,
    AttachmentLinkSerializer,
    ImageSerializer,
)


class AttachmentLinkViewSet(viewsets.ModelViewSet):
    serializer_class = AttachmentLinkSerializer
    lookup_field = "id"
    lookup_value_regex = "[0-9]+"
    permission_classes = [
        IsAuthenticatedOrReadOnly,
        ReadOnly
        | HasBasePermission("change_project", "projects")
        | HasOrganizationPermission("change_project")
        | HasProjectPermission("change_project"),
    ]

    def get_queryset(self) -> QuerySet:
        qs = self.request.user.get_project_related_queryset(AttachmentLink.objects)
        if "project_id" in self.kwargs:

            # TODO : handle with MultipleIDViewsetMixin
            project = Project.objects.filter(slug=self.kwargs["project_id"])
            if project.exists():
                self.kwargs["project_id"] = project.get().id

            return qs.filter(project=self.kwargs["project_id"])
        return qs


class AttachmentFileViewSet(viewsets.ModelViewSet):
    parser_classes = [MultiPartParser]
    serializer_class = AttachmentFileSerializer
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

    def get_queryset(self) -> QuerySet:
        qs = self.request.user.get_project_related_queryset(AttachmentFile.objects)
        if "project_id" in self.kwargs:

            # TODO : handle with MultipleIDViewsetMixin
            project = Project.objects.filter(slug=self.kwargs["project_id"])
            if project.exists():
                self.kwargs["project_id"] = project.get().id

            return qs.filter(project=self.kwargs["project_id"])
        return qs

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

    def process_image(self, image: ImageFile) -> File:
        """Allows to modify the image before saving it.

        For more information about the `ImageFile` object, see:
         * https://docs.djangoproject.com/en/4.0/ref/files/file/#the-file-class
         * https://docs.djangoproject.com/en/4.0/ref/files/file/#the-imagefile-class
        """
        # Check that image is not too large by calling serializer.is_valid()
        ImageSerializer(data={"name": image.name, "file": image}).is_valid(
            raise_exception=True
        )
        return image

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
        file = request.data["file"]
        file = self.process_image(file)
        filename = file._name
        image = Image(name=filename, file=file)
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
            return Response(
                f"You can't delete this picture: It is related to an instance of {relation['model']} with pk={relation['pk']} through field {relation['field']}.",
                status=status.HTTP_409_CONFLICT,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)
