from typing import Any, Dict, List, Optional

from rest_framework import serializers

from apps.accounts.serializers import UserLighterSerializer
from apps.commons.fields import RecursiveField, WritableSerializerMethodField
from apps.commons.serializers import (
    LazySerializer,
    OrganizationRelatedSerializer,
    ProjectRelatedSerializer,
    StringsImagesSerializer,
)
from apps.files.models import Image
from apps.organizations.models import Organization
from apps.projects.models import Project
from services.translator.serializers import AutoTranslatedModelSerializer

from .exceptions import (
    CommentProjectPermissionDeniedError,
    CommentReplyOnReplyError,
    CommentReplyToSelfError,
)
from .models import Comment, Follow, Review


class FollowSerializer(
    AutoTranslatedModelSerializer,
    OrganizationRelatedSerializer,
    ProjectRelatedSerializer,
    serializers.ModelSerializer,
):
    follower = UserLighterSerializer(many=False, read_only=True)
    project_id = serializers.PrimaryKeyRelatedField(
        write_only=True, queryset=Project.objects.all(), source="project"
    )
    project = LazySerializer(
        "apps.projects.serializers.ProjectLightSerializer", read_only=True
    )

    class Meta:
        model = Follow
        fields = [
            "id",
            "follower",
            "created_at",
            "updated_at",
            # read only
            "project",
            # write only
            "project_id",
        ]

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


class UserFollowManySerializer(serializers.Serializer):
    """Used to follow several projects at once."""

    follows = FollowSerializer(many=True)

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class ReviewSerializer(
    StringsImagesSerializer,
    AutoTranslatedModelSerializer,
    OrganizationRelatedSerializer,
    ProjectRelatedSerializer,
    serializers.ModelSerializer,
):
    string_images_forbid_fields: List[str] = ["title", "description"]

    reviewer = UserLighterSerializer(read_only=True)
    project_id = serializers.PrimaryKeyRelatedField(
        source="project", queryset=Project.objects.all()
    )

    class Meta:
        model = Review
        fields = [
            "id",
            "description",
            "title",
            "created_at",
            "updated_at",
            "project_id",
            # read only
            "reviewer",
        ]

    def get_related_organizations(self) -> List[Organization]:
        """Retrieve the related organizations"""
        if "project" in self.validated_data:
            return self.validated_data["project"].get_related_organizations()
        return []

    def get_related_project(self) -> Optional[Project]:
        """Retrieve the related projects"""
        if "project" in self.validated_data:
            return self.validated_data["project"]
        return None


class CommentSerializer(
    StringsImagesSerializer,
    AutoTranslatedModelSerializer,
    OrganizationRelatedSerializer,
    ProjectRelatedSerializer,
    serializers.ModelSerializer,
):

    string_images_fields: List[str] = ["content"]
    string_images_upload_to: str = "comment/images/"
    string_images_view: str = "Comment-images-detail"
    string_images_process_template: bool = True

    content = WritableSerializerMethodField(write_field=serializers.CharField())

    # read_only
    author = UserLighterSerializer(read_only=True)
    replies = RecursiveField(read_only=True, many=True)
    images = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    # write_only
    project_id = serializers.PrimaryKeyRelatedField(
        write_only=True, queryset=Project.objects.all(), source="project"
    )
    reply_on_id = serializers.PrimaryKeyRelatedField(
        write_only=True,
        queryset=Comment.objects.all(),
        source="reply_on",
        required=False,
        allow_null=True,
    )
    images_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        write_only=True,
        queryset=Image.objects.all(),
        source="images",
        required=False,
    )

    class Meta:
        model = Comment
        fields = [
            "id",
            "content",
            "created_at",
            "updated_at",
            "deleted_at",
            # write_only
            "project_id",
            "reply_on_id",
            "images_ids",
            # read only
            "replies",
            "author",
            "images",
        ]

    def get_content(self, comment: Comment) -> str:
        return "<deleted comment>" if comment.deleted_at else comment.content

    def validate_reply_on_id(self, reply_on: Comment):
        if reply_on.reply_on_id is not None:
            raise CommentReplyOnReplyError
        if self.instance and self.instance.pk == reply_on.pk:
            raise CommentReplyToSelfError
        return reply_on

    def validate_project_id(self, project: Project):
        """Ensure the project is public."""
        request = self.context.get("request")
        user = request.user
        if not user.get_project_queryset().contains(project):
            raise CommentProjectPermissionDeniedError(project.title)
        return project

    def get_string_images_kwargs(
        self, instance: Comment, field_name: str, *args: Any, **kwargs: Any
    ) -> Dict[str, Any]:
        """Get additional kwargs for image processing based on the instance."""
        return {"project_id": instance.project.id}

    def get_related_organizations(self) -> List[Organization]:
        """Retrieve the related organizations"""
        if "project" in self.validated_data:
            return self.validated_data["project"].get_related_organizations()
        return []

    def get_related_project(self) -> Optional[Project]:
        """Retrieve the related projects"""
        if "project" in self.validated_data:
            return self.validated_data["project"]
        return None
