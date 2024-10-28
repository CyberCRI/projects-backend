from typing import Any, Dict

from rest_framework import serializers

from apps.accounts.serializers import PeopleGroupLightSerializer, UserLighterSerializer
from apps.feedbacks.models import Follow
from apps.files.serializers import ImageSerializer
from apps.organizations.serializers import (
    OrganizationLightSerializer,
    ProjectCategoryLightSerializer,
)
from apps.projects.models import Project
from apps.projects.utils import get_views_from_serializer

from .models import SearchObject


class ProjectSearchSerializer(serializers.ModelSerializer):
    categories = ProjectCategoryLightSerializer(many=True, read_only=True)
    header_image = ImageSerializer(read_only=True)
    organizations = OrganizationLightSerializer(many=True, read_only=True)
    is_followed = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Project
        fields = [
            "id",
            "title",
            "slug",
            "purpose",
            "language",
            "organizations",
            "header_image",
            "categories",
            "created_at",
            "updated_at",
            "publication_status",
            "sdgs",
            "life_status",
            "is_followed",
        ]

    get_views = get_views_from_serializer

    def get_is_followed(self, project: Project) -> Dict[str, Any]:
        if "request" in self.context:
            user = self.context["request"].user
            if not user.is_anonymous:
                follow = Follow.objects.filter(follower=user, project=project)
                if follow.exists():
                    return {"is_followed": True, "follow_id": follow.first().id}
        return {"is_followed": False, "follow_id": None}


class SearchObjectSerializer(serializers.ModelSerializer):
    project = ProjectSearchSerializer(read_only=True)
    user = UserLighterSerializer(read_only=True)
    people_group = PeopleGroupLightSerializer(read_only=True)

    class Meta:
        model = SearchObject
        read_only_fields = ["id", "type", "project", "user", "people_group"]
        fields = read_only_fields
