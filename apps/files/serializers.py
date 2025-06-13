import hashlib
import re
from typing import List, Optional
from urllib.parse import urlparse

import requests
from azure.core.exceptions import AzureError
from bs4 import BeautifulSoup
from django.conf import settings
from django.http import QueryDict
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from apps.commons.serializers import (
    OrganizationRelatedSerializer,
    ProjectRelatedSerializer,
)
from apps.organizations.models import Organization
from apps.projects.models import Project

from .exceptions import (
    ChangeFileProjectError,
    ChangeLinkProjectError,
    DuplicatedFileError,
    DuplicatedLinkError,
    DuplicatedOrganizationFileError,
    FileTooLargeError,
)
from .models import (
    AttachmentFile,
    AttachmentLink,
    AttachmentType,
    Image,
    OrganizationAttachmentFile,
)


# From https://github.com/glemmaPaul/django-stdimage-serializer (however the repo is not maintained anymore)
class StdImageField(serializers.ImageField):
    """
    Get all the variations of the StdImageField
    """

    def to_native(self, obj):
        return self.get_variations_urls(obj)

    def to_representation(self, obj):
        return self.get_variations_urls(obj)

    def get_variations_urls(self, obj):
        """
        Get all the logo urls.
        """

        # Initiate return object
        return_object = {}

        # Get the field of the object
        field = obj.field

        # A lot of ifs going araound, first check if it has the field variations
        if hasattr(field, "variations"):
            # Get the variations
            variations = field.variations
            # Go through the variations dict
            for key in variations.keys():
                # Just to be sure if the stdimage object has it stored in the obj
                if hasattr(obj, key):
                    # get the by stdimage properties
                    field_obj = getattr(obj, key, None)
                    if field_obj and hasattr(field_obj, "url"):
                        # store it, with the name of the variation type into our return object
                        return_object[key] = super(
                            StdImageField, self
                        ).to_representation(field_obj)

        # Also include the original (if possible)
        if hasattr(obj, "url"):
            return_object["original"] = super(StdImageField, self).to_representation(
                obj
            )

        return return_object


class AttachmentLinkSerializer(
    OrganizationRelatedSerializer, ProjectRelatedSerializer, serializers.ModelSerializer
):
    project_id = serializers.PrimaryKeyRelatedField(
        many=False, write_only=True, queryset=Project.objects.all(), source="project"
    )
    preview_image_url = serializers.URLField(max_length=2048, read_only=True)
    site_name = serializers.CharField(max_length=255, read_only=True)

    class Meta:
        model = AttachmentLink
        fields = [
            "id",
            "project_id",
            "attachment_type",
            "category",
            "description",
            "site_url",
            "preview_image_url",
            "site_name",
            "title",
        ]
        validators = [
            UniqueTogetherValidator(
                queryset=AttachmentLink.objects.all(),
                fields=["project_id", "site_url"],
                message="This url is already attached to this project.",
            )
        ]

    def to_internal_value(self, data):
        query_dict = QueryDict(mutable=True)
        query_dict.update(data)
        if "site_url" in data and not re.match(r"^https?://", data.get("site_url", "")):
            query_dict["site_url"] = f'https://{data["site_url"]}'
        instance = super().to_internal_value(query_dict)
        self.get_url_metadata(instance)
        return instance

    def get_url_response(self, instance):
        try:
            response = requests.get(
                instance.get("site_url", ""), timeout=settings.REQUESTS_DEFAULT_TIMEOUT
            )
        except (requests.exceptions.MissingSchema, requests.exceptions.ConnectionError):
            return None
        return response

    def get_url_metadata(self, instance):
        # Get metadata if website is reachable
        response = self.get_url_response(instance)
        if not response:
            return
        soup = BeautifulSoup(response.text, "html.parser")
        instance["site_name"] = self.find_site_name(soup, instance.get("site_url"))
        instance["preview_image_url"] = self.find_preview_image_url(
            soup, instance.get("site_url")
        )
        instance["attachment_type"] = self.find_attachment_type(soup)

    def validate_site_url(self, site_url):
        project_id = None
        if "project_id" in self.initial_data:
            project_id = self.initial_data["project_id"]
        elif self.instance:
            project_id = self.instance.project.id
        if (
            project_id
            and self.instance
            and self.Meta.model.objects.filter(project=project_id, site_url=site_url)
            .exclude(id=self.instance.id)
            .exists()
        ):
            raise DuplicatedLinkError
        if (
            project_id
            and not self.instance
            and self.Meta.model.objects.filter(
                project=project_id, site_url=site_url
            ).exists()
        ):
            raise DuplicatedLinkError
        return site_url

    def validate_project_id(self, project):
        if self.instance and self.instance.project != project:
            raise ChangeLinkProjectError
        return project

    @staticmethod
    def find_attribute(soup, attr):
        attribute = soup.find(
            lambda tag: tag.name == "meta"
            and (
                ("name" in tag.attrs and tag.attrs["name"] == f"twitter:{attr}")
                or ("property" in tag.attrs and tag.attrs["property"] == f"og:{attr}")
            )
        )
        return attribute["content"] if attribute else ""

    def find_site_name(self, soup, url):
        site_name = self.find_attribute(soup, "site_name")
        return site_name if site_name != "" else f"{urlparse(url).netloc}"

    def find_preview_image_url(self, soup, url):
        preview_image_url = self.find_attribute(soup, "image")
        if preview_image_url != "":
            return preview_image_url
        try:
            requests.get(
                f"{urlparse(url).scheme}://{urlparse(url).netloc}/favicon.ico",
                timeout=1,
            )
            return f"https://api.faviconkit.com/{urlparse(url).netloc}/128"
        except Exception:  # noqa: PIE786
            return ""

    @staticmethod
    def find_attachment_type(soup):
        if soup.find(
            lambda tag: (
                "property" in tag.attrs and tag.attrs["property"] == "og:video:type"
            )
        ):
            return AttachmentType.VIDEO
        if soup.find(
            lambda tag: (
                "property" in tag.attrs and tag.attrs["property"] == "og:image:type"
            )
        ):
            return AttachmentType.IMAGE
        return AttachmentType.LINK

    def get_related_organizations(self) -> List[Organization]:
        """Retrieve the related organizations"""
        if "project" in self.validated_data:
            return self.validated_data["project"].get_related_organizations()
        return []


class OrganizationAttachmentFileSerializer(serializers.ModelSerializer):
    file = serializers.FileField()
    hashcode = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = OrganizationAttachmentFile
        fields = [
            "id",
            "file",
            "title",
            "description",
            "attachment_type",
            "mime",
            "hashcode",
        ]

    def to_internal_value(self, data):
        if "file" in data:
            file = data["file"]
            data["hashcode"] = hashlib.sha256(file.read()).hexdigest()
            file.seek(0)  # Reset file position so it starts at 0
        elif "hashcode" in data:
            del data["hashcode"]
        return super().to_internal_value(data)

    def validate_hashcode(self, hashcode: str):
        organization_code = self.context.get("organization_code", None)
        if organization_code:
            queryset = self.Meta.model.objects.filter(
                organization__code=organization_code, hashcode=hashcode
            )
            if self.instance:
                queryset = queryset.exclude(id=self.instance.id)
            if queryset.exists():
                raise DuplicatedOrganizationFileError
        return hashcode

    def validate_file(self, file):
        limit = settings.MAX_FILE_SIZE * 1024 * 1024
        if file.size > limit:
            raise FileTooLargeError
        return file


class AttachmentFileSerializer(
    OrganizationRelatedSerializer, ProjectRelatedSerializer, serializers.ModelSerializer
):
    project_id = serializers.PrimaryKeyRelatedField(
        many=False, write_only=True, queryset=Project.objects.all(), source="project"
    )
    file = serializers.FileField()
    hashcode = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = AttachmentFile
        fields = [
            "id",
            "project_id",
            "file",
            "title",
            "description",
            "attachment_type",
            "mime",
            "hashcode",
        ]

    def to_internal_value(self, data):
        if "file" in data:
            file = data["file"]
            data["hashcode"] = hashlib.sha256(file.read()).hexdigest()
            file.seek(0)  # Reset file position so it starts at 0
        elif "hashcode" in data:
            del data["hashcode"]
        return super().to_internal_value(data)

    def validate_hashcode(self, hashcode):
        project_id = None
        if "project_id" in self.initial_data:
            project_id = self.initial_data["project_id"]
        elif self.instance:
            project_id = self.instance.project.id
        if (
            project_id
            and self.instance
            and self.Meta.model.objects.filter(project=project_id, hashcode=hashcode)
            .exclude(id=self.instance.id)
            .exists()
        ):
            raise DuplicatedFileError
        if (
            project_id
            and not self.instance
            and self.Meta.model.objects.filter(
                project=project_id, hashcode=hashcode
            ).exists()
        ):
            raise DuplicatedFileError
        return hashcode

    def validate_project_id(self, project):
        if self.instance and self.instance.project != project:
            raise ChangeFileProjectError
        return project

    def validate_file(self, file):
        limit = settings.MAX_FILE_SIZE * 1024 * 1024
        if file.size > limit:
            raise FileTooLargeError
        return file

    def get_related_organizations(self) -> List[Organization]:
        """Retrieve the related organizations"""
        if "project" in self.validated_data:
            return self.validated_data["project"].get_related_organizations()
        return []

    def get_related_project(self) -> Optional["Project"]:
        """Retrieve the related projects"""
        if "project" in self.validated_data:
            return self.validated_data["project"]
        return None


class ImageSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    file = serializers.ImageField(write_only=True)
    variations = StdImageField(source="file", read_only=True)

    class Meta:
        model = Image
        fields = [
            "id",
            "name",
            "url",
            "height",
            "width",
            "natural_ratio",
            "scale_x",
            "scale_y",
            "left",
            "top",
            "created_at",
            "file",
            "variations",
        ]

    def validate_file(self, file):
        limit = settings.MAX_FILE_SIZE * 1024 * 1024
        if file.size > limit:
            raise FileTooLargeError
        return file

    def get_url(self, image: Image) -> Optional[str]:
        try:
            url = image.file.url
        except AttributeError:
            return None
        request = self.context.get("request", None)
        if request is not None:
            return request.build_absolute_uri(url)
        return url

    def to_representation(self, instance):
        try:
            return super().to_representation(instance)
        except AzureError:
            return {
                "id": instance.id,
                "name": instance.name,
                "created_at": instance.created_at,
                "url": None,
                "height": None,
                "width": None,
                "natural_ratio": None,
                "scale_x": None,
                "scale_y": None,
                "left": None,
                "top": None,
            }
