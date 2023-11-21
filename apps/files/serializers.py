import hashlib
import re
from pictures.contrib.rest_framework import PictureField
from typing import List, Optional
from urllib.parse import urlparse

import requests
from azure.core.exceptions import AzureError
from bs4 import BeautifulSoup
from django.conf import settings
from django.http import QueryDict
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.validators import UniqueTogetherValidator

from apps.commons.serializers import (
    OrganizationRelatedSerializer,
    ProjectRelatedSerializer,
)
from apps.files.models import AttachmentFile, AttachmentLink, AttachmentType, Image
from apps.files.validators import file_size
from apps.organizations.models import Organization
from apps.projects.models import Project


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
        self.validate_url(instance)
        return instance

    def validate_url(self, instance):
        # Get metadata if website is reachable
        try:
            response = requests.get(
                instance.get("site_url", ""), timeout=settings.REQUESTS_DEFAULT_TIMEOUT
            )
        except (requests.exceptions.MissingSchema, requests.exceptions.ConnectionError):
            return

        soup = BeautifulSoup(response.text, "html.parser")
        instance["site_name"] = self.find_site_name(soup, instance.get("site_url"))
        instance["preview_image_url"] = self.find_preview_image_url(
            soup, instance.get("site_url")
        )
        instance["attachment_type"] = self.find_attachment_type(soup)

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


class AttachmentFileSerializer(
    OrganizationRelatedSerializer, ProjectRelatedSerializer, serializers.ModelSerializer
):
    project_id = serializers.PrimaryKeyRelatedField(
        many=False, write_only=True, queryset=Project.objects.all(), source="project"
    )
    file = serializers.FileField(validators=[file_size])

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
        ]

    def validate(self, data):
        if "file" in data:
            file = data["file"]
            hashcode = hashlib.sha256(file.read()).hexdigest()
            file.seek(0)  # Reset file position so it starts at 0
            if self.Meta.model.objects.filter(
                project_id=data["project"].id, hashcode=hashcode
            ).exists():
                raise ValidationError(
                    {
                        "error": "The file you are trying to upload is already attached to this project."
                    }
                )
            data["hashcode"] = hashcode
        return data

    def get_related_organizations(self) -> List[Organization]:
        """Retrieve the related organizations"""
        if "project" in self.validated_data:
            return self.validated_data["project"].get_related_organizations()
        return []

    def get_related_projects(self) -> List[Project]:
        """Retrieve the related projects"""
        if "project" in self.validated_data:
            return [self.validated_data["project"]]
        return []


class ImageSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    file = serializers.ImageField(validators=[file_size], write_only=True)
    variations = PictureField(source="file", read_only=True)

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
