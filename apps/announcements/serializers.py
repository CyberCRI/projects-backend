from typing import List, Optional

from drf_recaptcha.fields import ReCaptchaV2Field
from rest_framework import serializers

from apps.commons.serializers import (
    OrganizationRelatedSerializer,
    ProjectRelatedSerializer,
    StringsImagesSerializer,
)
from apps.files.serializers import ImageSerializer
from apps.organizations.models import Organization
from apps.projects.models import Project
from services.translator.serializers import AutoTranslatedModelSerializer

from .models import Announcement


class ProjectAnnouncementSerializer(
    AutoTranslatedModelSerializer, serializers.ModelSerializer
):
    header_image = ImageSerializer(read_only=True)

    class Meta:
        model = Project
        fields = [
            "id",
            "title",
            "slug",
            "purpose",
            "publication_status",
            "header_image",
            "language",
        ]


class AnnouncementSerializer(
    StringsImagesSerializer,
    AutoTranslatedModelSerializer,
    OrganizationRelatedSerializer,
    ProjectRelatedSerializer,
    serializers.ModelSerializer,
):

    string_images_forbid_fields: List[str] = ["title", "description"]

    project = ProjectAnnouncementSerializer(read_only=True)
    project_id = serializers.PrimaryKeyRelatedField(
        many=False, queryset=Project.objects.all(), source="project", write_only=True
    )

    class Meta:
        model = Announcement
        fields = [
            "id",
            "description",
            "title",
            "type",
            "status",
            "deadline",
            "is_remunerated",
            "created_at",
            "updated_at",
            # read_only
            "project",
            # write_only
            "project_id",
        ]

    def get_related_organizations(self) -> List[Organization]:
        """Retrieve the related organizations"""
        if "organizations" in self.validated_data:
            return self.validated_data["organizations"]
        if "project" in self.validated_data:
            return self.validated_data["project"].get_related_organizations()
        return []

    def get_related_project(self) -> Optional[Project]:
        """Retrieve the related projects"""
        if "project" in self.validated_data:
            return self.validated_data["project"]
        return None


class ApplyToAnnouncementSerializer(AnnouncementSerializer):
    applicant_name = serializers.CharField()
    applicant_firstname = serializers.CharField()
    applicant_email = serializers.EmailField()
    applicant_message = serializers.CharField()
    recaptcha = ReCaptchaV2Field()
    announcement = AnnouncementSerializer(read_only=True)
    announcement_id = serializers.PrimaryKeyRelatedField(
        many=False,
        queryset=Announcement.objects.all(),
        source="announcement",
        write_only=True,
    )

    class Meta:
        model = Announcement
        fields = [
            "project_id",
            "applicant_name",
            "applicant_firstname",
            "applicant_email",
            "applicant_message",
            "recaptcha",
            # read_only
            "announcement",
            # write_only
            "announcement_id",
        ]
