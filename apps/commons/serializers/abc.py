from typing import List

from rest_framework import serializers

from apps.organizations.models import Organization
from apps.projects.models import Project


class OrganizationRelatedSerializer(serializers.ModelSerializer):
    """Base serializer for serializers related to organizations."""

    def get_related_organizations(self) -> List[Organization]:
        """Retrieve the related organizations"""
        raise NotImplementedError()


class ProjectRelatedSerializer(serializers.ModelSerializer):
    """Base serializer for serializers related to projects."""

    def get_related_projects(self) -> List[Project]:
        """Retrieve the related projects"""
        raise NotImplementedError()
