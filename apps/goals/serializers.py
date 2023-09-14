from typing import List

from rest_framework import serializers

from apps.commons.serializers import (
    OrganizationRelatedSerializer,
    ProjectRelatedSerializer,
)
from apps.goals import models
from apps.organizations.models import Organization
from apps.projects.models import Project


class GoalSerializer(
    OrganizationRelatedSerializer, ProjectRelatedSerializer, serializers.ModelSerializer
):
    project_id = serializers.PrimaryKeyRelatedField(
        many=False, write_only=True, queryset=Project.objects.all(), source="project"
    )

    class Meta:
        model = models.Goal
        fields = [
            "id",
            "title",
            "description",
            "deadline_at",
            "status",
            "project_id",
        ]

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
