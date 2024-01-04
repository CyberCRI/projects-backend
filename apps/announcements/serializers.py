from typing import List

from drf_recaptcha.fields import ReCaptchaV2Field
from rest_framework import serializers

from apps.commons.serializers import (
    OrganizationRelatedSerializer,
    ProjectRelatedSerializer,
)
from apps.files.serializers import ImageSerializer
from apps.organizations.models import Organization
from apps.organizations.serializers import (
    OrganizationLightSerializer,
    OrganizationSerializer,
    ProjectCategorySerializer,
)
from apps.projects.models import Project
from apps.projects.utils import get_views_from_serializer

from .models import Announcement


class ProjectAnnouncementSerializer(serializers.ModelSerializer):
    categories = ProjectCategorySerializer(many=True, read_only=True)
    header_image = ImageSerializer(read_only=True)
    organizations = OrganizationSerializer(many=True, read_only=True)
    views = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = [
            "id",
            "title",
            "slug",
            "purpose",
            "publication_status",
            "categories",
            "header_image",
            "language",
            "organizations",
            "views",
        ]

    get_views = get_views_from_serializer


class AnnouncementSerializer(
    OrganizationRelatedSerializer, ProjectRelatedSerializer, serializers.ModelSerializer
):
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

    def get_organizations(self, announcement: Announcement) -> dict:
        organizations = OrganizationLightSerializer(
            announcement.project.organizations, many=True
        )
        return organizations.data

    def get_related_organizations(self) -> List[Organization]:
        """Retrieve the related organizations"""
        if "organizations" in self.validated_data:
            return self.validated_data["organizations"]
        if "project" in self.validated_data:
            return self.validated_data["project"].get_related_organizations()
        return []

    def get_related_projects(self) -> List[Project]:
        """Retrieve the related projects"""
        if "project" in self.validated_data:
            return [self.validated_data["project"]]
        return []


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
