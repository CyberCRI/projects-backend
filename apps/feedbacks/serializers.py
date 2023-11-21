from typing import List

from django.db import transaction
from rest_framework import exceptions, serializers

from apps.accounts.serializers import UserLightSerializer
from apps.commons.serializers import (
    LazySerializer,
    OrganizationRelatedSerializer,
    ProjectRelatedSerializer,
    RecursiveField,
    WritableSerializerMethodField,
)
from apps.commons.utils.process_text import process_text
from apps.files.models import Image
from apps.organizations.models import Organization
from apps.projects.models import Project

from .models import Comment, Follow, Review


class FollowSerializer(
    OrganizationRelatedSerializer, ProjectRelatedSerializer, serializers.ModelSerializer
):
    follower = UserLightSerializer(many=False, read_only=True)
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

    def get_related_projects(self) -> List[Project]:
        """Retrieve the related projects"""
        if "project" in self.validated_data:
            return [self.validated_data["project"]]
        return []


class UserFollowManySerializer(serializers.Serializer):
    """Used to follow several projects at once."""

    follows = FollowSerializer(many=True)

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class ReviewSerializer(
    OrganizationRelatedSerializer, ProjectRelatedSerializer, serializers.ModelSerializer
):
    reviewer = UserLightSerializer(read_only=True)
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

    def get_related_projects(self) -> List[Project]:
        """Retrieve the related projects"""
        if "project" in self.validated_data:
            return [self.validated_data["project"]]
        return []


class CommentSerializer(
    OrganizationRelatedSerializer, ProjectRelatedSerializer, serializers.ModelSerializer
):
    content = WritableSerializerMethodField(write_field=serializers.CharField())

    # read_only
    author = UserLightSerializer(read_only=True)
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

    def validate(self, data):
        """Ensure no 2nd level replies are created."""
        if "reply_on" in data and data["reply_on"].reply_on_id is not None:
            raise serializers.ValidationError(
                {"reply_on_id": "You cannot reply to a reply."}
            )
        return data

    def validate_project_id(self, project: Project):
        """Ensure the project is public."""
        request = self.context.get("request")
        user = request.user
        if project not in user.get_project_queryset():
            raise exceptions.PermissionDenied(
                {
                    "project_id": "You cannot comment on a project you don't have access to."
                }
            )
        return project

    @transaction.atomic
    def save(self, **kwargs):
        if "content" in self.validated_data:
            if not self.instance:
                super(CommentSerializer, self).save(**kwargs)
            text, images = process_text(
                self.context["request"],
                self.instance.project,
                self.validated_data["content"],
                "comment/images/",
                "Comment-images-detail",
                project_id=self.instance.project.id,
            )
            self.validated_data["content"] = text
            self.validated_data["images"] = images + [
                image for image in self.instance.images.all()
            ]
        instance = super(CommentSerializer, self).save(**kwargs)
        instance.project.save()
        return instance

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
