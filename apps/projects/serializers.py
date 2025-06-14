from typing import Any, Dict, List, Optional

from django.apps import apps
from django.contrib.auth.models import Group
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import serializers

from apps.accounts.models import AnonymousUser, PeopleGroup, ProjectUser
from apps.accounts.serializers import PeopleGroupLightSerializer, UserLighterSerializer
from apps.announcements.serializers import AnnouncementSerializer
from apps.commons.fields import (
    HiddenPrimaryKeyRelatedField,
    RecursiveField,
    UserMultipleIdRelatedField,
    WritableSerializerMethodField,
)
from apps.commons.models import GroupData
from apps.commons.serializers import (
    OrganizationRelatedSerializer,
    ProjectRelatedSerializer,
)
from apps.commons.utils import process_text
from apps.feedbacks.models import Comment, Follow
from apps.feedbacks.serializers import CommentSerializer, ReviewSerializer
from apps.files.models import Image
from apps.files.serializers import (
    AttachmentFileSerializer,
    AttachmentLinkSerializer,
    ImageSerializer,
)
from apps.notifications.tasks import notify_project_changes
from apps.organizations.models import Organization, ProjectCategory
from apps.organizations.serializers import (
    OrganizationSerializer,
    ProjectCategoryLightSerializer,
    TemplateSerializer,
)
from apps.skills.models import Tag
from apps.skills.serializers import TagRelatedField

from .exceptions import (
    AddProjectToOrganizationPermissionError,
    EmptyProjectDescriptionError,
    LinkProjectToSelfError,
    OnlyReviewerCanChangeStatusError,
    ProjectCategoryOrganizationError,
    ProjectMessageReplyOnReplyError,
    ProjectMessageReplyToSelfError,
    ProjectTabChangeTypeError,
    ProjectWithNoOrganizationError,
    RemoveLastProjectOwnerError,
)
from .models import (
    BlogEntry,
    Goal,
    LinkedProject,
    Location,
    Project,
    ProjectMessage,
    ProjectTab,
    ProjectTabItem,
)
from .utils import compute_project_changes, get_views_from_serializer


class BlogEntrySerializer(
    OrganizationRelatedSerializer, ProjectRelatedSerializer, serializers.ModelSerializer
):
    project_id = serializers.PrimaryKeyRelatedField(
        many=False, write_only=True, queryset=Project.objects.all(), source="project"
    )
    images_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        write_only=True,
        queryset=Image.objects.all(),
        source="images",
        required=False,
    )
    images = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = BlogEntry
        fields = [
            "id",
            "title",
            "content",
            "created_at",
            "updated_at",
            # read only
            "images",
            # write only
            "project_id",
            "images_ids",
        ]

    @transaction.atomic
    def save(self, **kwargs):
        if "content" in self.validated_data:
            create = not self.instance
            if create:
                super(BlogEntrySerializer, self).save(**kwargs)
            text, images = process_text(
                request=self.context["request"],
                instance=self.instance,
                text=self.validated_data["content"],
                upload_to="blog_entry/images/",
                view="BlogEntry-images-detail",
                process_template=True,
                project_id=self.instance.project.id,
            )
            if create and not images and text == self.validated_data["content"]:
                return self.instance
            self.validated_data["content"] = text
            self.validated_data["images"] = images + [
                image for image in self.instance.images.all()
            ]
        return super(BlogEntrySerializer, self).save(**kwargs)

    @transaction.atomic
    def update(self, instance, validated_data):
        if "created_at" in self.initial_data:
            BlogEntry.objects.filter(id=instance.id).update(
                created_at=self.initial_data["created_at"]
            )
            instance.refresh_from_db()
        return super(BlogEntrySerializer, self).update(instance, validated_data)

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


class GoalSerializer(
    OrganizationRelatedSerializer, ProjectRelatedSerializer, serializers.ModelSerializer
):
    project_id = serializers.PrimaryKeyRelatedField(
        many=False, write_only=True, queryset=Project.objects.all(), source="project"
    )

    class Meta:
        model = Goal
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

    def get_related_project(self) -> Optional[Project]:
        """Retrieve the related projects"""
        if "project" in self.validated_data:
            return self.validated_data["project"]
        return None


class LocationProjectSerializer(serializers.ModelSerializer):
    header_image = ImageSerializer(read_only=True)

    class Meta:
        model = Project
        fields = ["id", "slug", "title", "purpose", "header_image"]


class LocationSerializer(
    OrganizationRelatedSerializer, ProjectRelatedSerializer, serializers.ModelSerializer
):
    project = LocationProjectSerializer(read_only=True)
    project_id = serializers.PrimaryKeyRelatedField(
        many=False, write_only=True, queryset=Project.objects.all(), source="project"
    )

    class Meta:
        model = Location
        fields = [
            "id",
            "title",
            "description",
            "lat",
            "lng",
            "type",
            "project",
            # write_only
            "project_id",
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


class ProjectSuperLightSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ["id", "slug", "title"]


class ProjectLightSerializer(serializers.ModelSerializer):
    categories = ProjectCategoryLightSerializer(many=True, read_only=True)
    header_image = ImageSerializer(read_only=True)
    is_followed = serializers.SerializerMethodField(read_only=True)
    is_featured = serializers.BooleanField(read_only=True, required=False)
    is_group_project = serializers.BooleanField(read_only=True, required=False)

    class Meta:
        model = Project
        fields = [
            "id",
            "slug",
            "title",
            "purpose",
            "categories",
            "header_image",
            "language",
            "publication_status",
            "life_status",
            "created_at",
            "updated_at",
            "is_followed",
            "is_featured",
            "is_group_project",
        ]

    def get_is_followed(self, project: Project) -> Dict[str, Any]:
        if "request" in self.context:
            user = self.context["request"].user
            if not user.is_anonymous:
                follow = Follow.objects.filter(follower=user, project=project)
                if follow.exists():
                    return {"is_followed": True, "follow_id": follow.first().id}
        return {"is_followed": False, "follow_id": None}


class ProjectRemoveLinkedProjectSerializer(serializers.ModelSerializer):
    """Used to unlink projects from a project."""

    project_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        write_only=True,
        queryset=Project.objects.all(),
        source="linked_projects",
    )

    class Meta:
        model = LinkedProject
        fields = ["project_ids"]


class LinkedProjectSerializer(serializers.ModelSerializer):
    project = ProjectLightSerializer(read_only=True)
    project_id = serializers.PrimaryKeyRelatedField(
        write_only=True, queryset=Project.objects.all(), source="project"
    )
    target_id = serializers.PrimaryKeyRelatedField(
        write_only=True, queryset=Project.objects.all(), source="target"
    )

    class Meta:
        model = LinkedProject
        fields = ["id", "project_id", "target_id", "project"]

    def validate(self, data):
        project = None
        target = None
        if "project" in data:
            project = data["project"]
        elif self.instance:
            project = self.instance.project
        if "target" in data:
            target = data["target"]
        elif self.instance:
            target = self.instance.target
        if project and target and project == target:
            raise LinkProjectToSelfError(target.title)
        return data


class ProjectAddLinkedProjectSerializer(serializers.Serializer):
    """Used to link projects to another one."""

    projects = LinkedProjectSerializer(many=True)

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class ProjectIdSerializer(serializers.Serializer):
    """Used to retrieve a project from their `id`."""

    project = serializers.PrimaryKeyRelatedField(queryset=Project.objects.all())


class UserLighterSerializerKeycloakRelatedField(
    UserLighterSerializer, UserMultipleIdRelatedField
):
    def to_representation(self, instance):
        return UserLighterSerializer.to_representation(self, instance)

    def to_internal_value(self, data):
        return UserMultipleIdRelatedField.to_internal_value(self, data)


class PeopleGroupLightSerializerPrimaryKeyRelatedField(
    PeopleGroupLightSerializer, serializers.PrimaryKeyRelatedField
):
    def to_representation(self, instance):
        return PeopleGroupLightSerializer.to_representation(self, instance)

    def to_internal_value(self, data):
        return serializers.PrimaryKeyRelatedField.to_internal_value(self, data)


class ProjectAddTeamMembersSerializer(serializers.Serializer):
    project = HiddenPrimaryKeyRelatedField(
        required=False, write_only=True, queryset=Project.objects.all()
    )
    members = UserLighterSerializerKeycloakRelatedField(
        many=True, required=False, queryset=ProjectUser.objects.all()
    )
    owners = UserLighterSerializerKeycloakRelatedField(
        many=True, required=False, queryset=ProjectUser.objects.all()
    )
    reviewers = UserLighterSerializerKeycloakRelatedField(
        many=True, required=False, queryset=ProjectUser.objects.all()
    )
    member_groups = PeopleGroupLightSerializerPrimaryKeyRelatedField(
        many=True, required=False, queryset=PeopleGroup.objects.all()
    )
    owner_groups = PeopleGroupLightSerializerPrimaryKeyRelatedField(
        many=True, required=False, queryset=PeopleGroup.objects.all()
    )
    reviewer_groups = PeopleGroupLightSerializerPrimaryKeyRelatedField(
        many=True, required=False, queryset=PeopleGroup.objects.all()
    )

    def add_user(
        self, user: ProjectUser, project: Project, group: Group, role: str
    ) -> Dict[str, Any]:
        created = not project.groups.filter(users=user).exists()
        if (
            group.name == project.get_reviewers().name
            and not group.users.all().exists()
            and project.main_category is not None
            and project.main_category.only_reviewer_can_publish
        ):
            project.publication_status = Project.PublicationStatus.PRIVATE
            project.save()
        user.groups.remove(*project.groups.filter(users=user))
        user.groups.add(group)
        return {
            "type": "projectuser",
            "created": created,
            "user": user,
            "project": project,
            "group": group,
            "role": role,
        }

    def add_people_group(
        self, people_group: PeopleGroup, project: Project, group: Group, role: str
    ) -> Dict[str, Any]:
        created = not project.groups.filter(people_groups=people_group).exists()
        people_group.groups.remove(*project.groups.filter(people_groups=people_group))
        people_group.groups.add(group)
        project.set_role_group_members(group)
        return {
            "type": "peoplegroup",
            "created": created,
            "people_group": people_group,
            "project": project,
            "group": group,
            "role": role,
        }

    def create(self, validated_data):
        validated_data = validated_data.get("team", validated_data)
        project = validated_data["project"]
        instances = []
        for role in [
            GroupData.Role.OWNERS,
            GroupData.Role.REVIEWERS,
            GroupData.Role.MEMBERS,
        ]:
            users = validated_data.get(role, [])
            group = getattr(project, f"get_{role}")()
            for user in users:
                instances.append(self.add_user(user, project, group, role))
        for role in [
            GroupData.Role.OWNER_GROUPS,
            GroupData.Role.REVIEWER_GROUPS,
            GroupData.Role.MEMBER_GROUPS,
        ]:
            people_groups = validated_data.get(role, [])
            group = getattr(project, f"get_{role}")()
            for people_group in people_groups:
                instances.append(
                    self.add_people_group(people_group, project, group, role)
                )
        return instances

    def to_internal_value(self, data):
        return {"team": dict(super().to_internal_value(data))}


class ProjectRemoveTeamMembersSerializer(serializers.Serializer):
    project = HiddenPrimaryKeyRelatedField(
        write_only=True, queryset=Project.objects.all()
    )
    users = UserMultipleIdRelatedField(
        many=True, write_only=True, required=False, queryset=ProjectUser.objects.all()
    )
    people_groups = serializers.PrimaryKeyRelatedField(
        many=True, write_only=True, required=False, queryset=PeopleGroup.objects.all()
    )

    def validate_users(self, users: List[ProjectUser]) -> List[ProjectUser]:
        project = get_object_or_404(Project, pk=self.initial_data["project"])
        if all(owner in users for owner in project.get_owners().users.all()):
            raise RemoveLastProjectOwnerError
        return list(filter(lambda x: x.groups.filter(projects=project).exists(), users))

    def validate_people_groups(
        self, people_groups: List[PeopleGroup]
    ) -> List[PeopleGroup]:
        project = get_object_or_404(Project, pk=self.initial_data["project"])
        return list(
            filter(lambda x: x.groups.filter(projects=project).exists(), people_groups)
        )

    def remove_users(self, validated_data):
        project = validated_data["project"]
        users = validated_data.get("users", [])
        for user in users:
            user.groups.remove(*project.groups.filter(users=user))
        return users

    def remove_people_groups(self, validated_data):
        project = validated_data["project"]
        people_groups = validated_data.get("people_groups", [])
        for people_group in people_groups:
            people_group.groups.remove(
                *project.groups.filter(people_groups=people_group)
            )
        project.set_role_groups_members()
        return people_groups

    def create(self, validated_data):
        return {
            "project": validated_data["project"],
            "users": self.remove_users(validated_data),
            "people_groups": self.remove_people_groups(validated_data),
        }


class ProjectSerializer(OrganizationRelatedSerializer, serializers.ModelSerializer):
    team = ProjectAddTeamMembersSerializer(required=False, source="*")
    tags = TagRelatedField(many=True, required=False)

    # read_only
    header_image = ImageSerializer(read_only=True)
    categories = ProjectCategoryLightSerializer(many=True, read_only=True)
    last_comment = serializers.SerializerMethodField(read_only=True)
    organizations = OrganizationSerializer(many=True, read_only=True)
    goals = GoalSerializer(many=True, read_only=True)
    reviews = ReviewSerializer(many=True, read_only=True)
    locations = LocationSerializer(many=True, read_only=True)
    announcements = AnnouncementSerializer(many=True, read_only=True)
    links = AttachmentLinkSerializer(many=True, read_only=True)
    files = AttachmentFileSerializer(many=True, read_only=True)
    images = ImageSerializer(many=True, read_only=True)
    blog_entries = BlogEntrySerializer(many=True, read_only=True)
    linked_projects = serializers.SerializerMethodField(read_only=True)
    template = serializers.SerializerMethodField()
    views = serializers.SerializerMethodField()
    is_followed = serializers.SerializerMethodField(read_only=True)

    # write_only
    header_image_id = serializers.PrimaryKeyRelatedField(
        write_only=True,
        queryset=Image.objects.all(),
        source="header_image",
        required=False,
    )
    project_categories_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        write_only=True,
        queryset=ProjectCategory.objects.all(),
        source="categories",
        required=False,
    )
    organizations_codes = serializers.SlugRelatedField(
        write_only=True,
        slug_field="code",
        source="organizations",
        queryset=Organization.objects.all(),
        many=True,
        required=True,
    )
    images_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        write_only=True,
        queryset=Image.objects.all(),
        source="images",
        required=False,
    )

    class Meta:
        model = Project
        read_only_fields = [
            "is_locked",
            "slug",
        ]
        fields = read_only_fields + [
            "id",
            "title",
            "description",
            "is_shareable",
            "purpose",
            "language",
            "publication_status",
            "life_status",
            "sdgs",
            "created_at",
            "updated_at",
            "deleted_at",
            "template",
            "tags",
            # read only
            "header_image",
            "categories",
            "last_comment",
            "organizations",
            "goals",
            "reviews",
            "locations",
            "announcements",
            "links",
            "files",
            "images",
            "blog_entries",
            "linked_projects",
            "views",
            "template",
            "is_followed",
            # write_only
            "project_categories_ids",
            "header_image_id",
            "organizations_codes",
            "images_ids",
            "team",
        ]

    @staticmethod
    def get_last_comment(project: Project) -> Optional[Dict]:
        recent = project.comments.filter(reply_on=None).order_by("-created_at")
        return CommentSerializer(recent.first()).data if recent.exists() else None

    def get_template(self, project: Project) -> Optional[Dict]:
        return (
            TemplateSerializer(project.main_category.template).data
            if project.main_category
            else None
        )

    def get_linked_projects(self, project: Project) -> Dict[str, Any]:
        queryset = LinkedProject.objects.filter(target=project)
        user = getattr(self.context.get("request", None), "user", AnonymousUser())
        queryset = user.get_project_related_queryset(queryset)
        return LinkedProjectSerializer(queryset, many=True).data

    def get_is_followed(self, project: Project) -> Dict[str, Any]:
        if "request" in self.context:
            user = self.context["request"].user
            if not user.is_anonymous:
                follow = Follow.objects.filter(follower=user, project=project)
                if follow.exists():
                    return {"is_followed": True, "follow_id": follow.first().id}
        return {"is_followed": False, "follow_id": None}

    @transaction.atomic
    def save(self, **kwargs):
        if "description" in self.validated_data:
            create = not self.instance
            if create:
                super(ProjectSerializer, self).save(**kwargs)
            text, images = process_text(
                request=self.context["request"],
                instance=self.instance,
                text=self.validated_data["description"],
                upload_to="project/images/",
                view="Project-images-detail",
                process_template=True,
                project_id=self.instance.id,
            )
            if create and not images and text == self.validated_data["description"]:
                return self.instance
            self.validated_data["description"] = text
            self.validated_data["images"] = images + [
                image for image in self.instance.images.all()
            ]
        return super(ProjectSerializer, self).save(**kwargs)

    def get_related_organizations(self) -> List[Organization]:
        """Retrieve the related organizations"""
        if "organizations" in self.validated_data:
            return self.validated_data["organizations"]
        return []

    def create(self, validated_data):
        categories = validated_data.get("categories", [])
        team = validated_data.pop("team", {})
        if len(categories) > 0:
            validated_data["main_category"] = categories[0]
        project = super(ProjectSerializer, self).create(validated_data)
        ProjectAddTeamMembersSerializer().create({"project": project, **team})
        return project

    def update(self, instance, validated_data):
        categories = validated_data.get("categories", [])
        validated_data.pop("team", {})
        if instance.main_category not in categories and len(categories) > 0:
            validated_data["main_category"] = categories[0]

        changes = compute_project_changes(instance, validated_data)
        notify_project_changes.delay(
            instance.pk, changes, self.context["request"].user.pk
        )
        return super(ProjectSerializer, self).update(instance, validated_data)

    def validate_organizations_codes(self, value: List[Organization]):
        if len(value) < 1:
            raise ProjectWithNoOrganizationError
        request = self.context.get("request", None)
        if request:
            organizations_to_add = (
                [o for o in value if o not in self.instance.organizations.all()]
                if self.instance
                else value
            )
            if not all(
                request.user.has_perm("organizations.add_project", organization)
                for organization in organizations_to_add
            ):
                raise AddProjectToOrganizationPermissionError
        return value

    def validate_publication_status(self, value: str):
        request = self.context["request"]
        user = request.user
        if (
            not self.instance
            or self.instance.publication_status == value
            or not getattr(
                self.instance.main_category, "only_reviewer_can_publish", False
            )
            or user.is_superuser
            or any(
                (user in o.admins.all() or user in o.facilitators.all())
                for o in self.instance.organizations.all()
            )
            or user in self.instance.reviewers.all()
            or user in self.instance.reviewer_groups_users.all()
        ):
            return value
        raise OnlyReviewerCanChangeStatusError

    # This is a fix to prevent bugs from hocus pocus
    # TODO: Remove this validation when history is implemented in the frontend
    def validate_description(self, value: str):
        if not self.instance:
            return value
        empty_descriptions = ["<p></p>", ""]
        if (
            self.instance.description not in empty_descriptions
            and value in empty_descriptions
        ):
            raise EmptyProjectDescriptionError
        return value

    def validate_categories(self, value: List[ProjectCategory]):
        organizations_codes = self.initial_data.get("organizations_codes", [])
        if self.instance and not organizations_codes:
            organizations_codes = self.instance.organizations.all().values_list(
                "code", flat=True
            )
        if not all(
            category.organization.code in organizations_codes for category in value
        ):
            raise ProjectCategoryOrganizationError
        return value

    get_views = get_views_from_serializer


class ProjectVersionSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField(read_only=True)
    project_id = serializers.SerializerMethodField(read_only=True)
    categories = serializers.SerializerMethodField(read_only=True)
    tags = serializers.SerializerMethodField(read_only=True)
    members = serializers.SerializerMethodField(read_only=True)
    comments = serializers.SerializerMethodField(read_only=True)
    linked_projects = serializers.SerializerMethodField(read_only=True)
    main_category = serializers.SlugRelatedField(read_only=True, slug_field="name")
    delta = serializers.SerializerMethodField(read_only=True)

    @staticmethod
    def get_id(version) -> int:
        return version.pk

    @staticmethod
    def get_project_id(version) -> str:
        return version.id

    @staticmethod
    def get_delta(version) -> Dict[str, str]:
        previous = version.prev_record
        while previous:
            previous_reason = previous.history_change_reason
            if previous_reason:
                delta = version.diff_against(previous)
                return {
                    change.field: {"old_version": change.old, "new_version": change.new}
                    for change in delta.changes
                }
            previous = previous.prev_record
        return {}

    @staticmethod
    def get_categories(version) -> List[str]:
        categories_ids = version.categories.all().values_list(
            "projectcategory_id", flat=True
        )
        return ProjectCategory.objects.filter(id__in=categories_ids).values_list(
            "name", flat=True
        )

    @staticmethod
    def get_tags(version) -> List[str]:
        tags_ids = version.tags.all().values_list("tag_id", flat=True)
        return Tag.objects.filter(id__in=tags_ids).values_list("title", flat=True)

    @staticmethod
    def get_members(version) -> List[str]:
        members = Project.objects.get(id=version.id).get_all_members()
        return [m.get_full_name() for m in members]

    @staticmethod
    def get_comments(version) -> Dict[str, Any]:
        comments = Comment.history.as_of(version.history_date).filter(
            project__id=version.id, deleted_at=None
        )
        return CommentSerializer(comments, many=True).data

    @staticmethod
    def get_linked_projects(version) -> Dict[str, Any]:
        linked_projects = LinkedProject.history.as_of(version.history_date).filter(
            target__id=version.id
        )
        return LinkedProjectSerializer(linked_projects, many=True).data

    class Meta:
        model = apps.get_model("projects", "HistoricalProject")
        fields = [
            "id",
            "project_id",
            "history_date",
            "history_change_reason",
            "delta",
            "title",
            "purpose",
            "description",
            "tags",
            "members",
            "comments",
            "linked_projects",
            "main_category",
            "categories",
        ]


class ProjectVersionListSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField(read_only=True)
    project_id = serializers.SerializerMethodField(read_only=True)
    updated_fields = serializers.SerializerMethodField(read_only=True)

    @staticmethod
    def get_id(version) -> int:
        return version.pk

    @staticmethod
    def get_project_id(version) -> str:
        return version.id

    @staticmethod
    def get_updated_fields(version) -> List[str]:
        previous = version.prev_record
        while previous:
            previous_reason = previous.history_change_reason
            if previous_reason:
                delta = version.diff_against(previous)
                return [change.field for change in delta.changes]
            previous = previous.prev_record
        return []

    class Meta:
        model = apps.get_model("projects", "HistoricalProject")
        fields = [
            "id",
            "project_id",
            "history_date",
            "history_change_reason",
            "updated_fields",
        ]


class ProjectMessageSerializer(serializers.ModelSerializer):
    content = WritableSerializerMethodField(write_field=serializers.CharField())
    reply_on = serializers.PrimaryKeyRelatedField(
        queryset=ProjectMessage.objects.all(),
        required=False,
        allow_null=True,
    )

    # read_only
    author = UserLighterSerializer(read_only=True)
    replies = RecursiveField(read_only=True, many=True)
    images = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = ProjectMessage
        fields = [
            "id",
            "content",
            "created_at",
            "updated_at",
            "deleted_at",
            "reply_on",
            # read only
            "author",
            "replies",
            "images",
        ]

    def get_content(self, message: ProjectMessage) -> str:
        return "<deleted message>" if message.deleted_at else message.content

    def validate_reply_on(self, reply_on: ProjectMessage):
        if reply_on.reply_on is not None:
            raise ProjectMessageReplyOnReplyError
        if self.instance and self.instance.pk == reply_on.pk:
            raise ProjectMessageReplyToSelfError
        return reply_on

    @transaction.atomic
    def save(self, **kwargs):
        if "content" in self.validated_data:
            create = not self.instance
            if create:
                super().save(**kwargs)
            text, images = process_text(
                request=self.context["request"],
                instance=self.instance,
                text=self.validated_data["content"],
                upload_to="project_messages/images/",
                view="ProjectMessage-images-detail",
                project_id=self.instance.project.id,
            )
            if create and not images and text == self.validated_data["content"]:
                return self.instance
            self.validated_data["content"] = text
            self.instance.images.add(*images)
        return super().save(**kwargs)


class ProjectTabSerializer(serializers.ModelSerializer):
    images = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Image.objects.all(), required=False
    )

    class Meta:
        model = ProjectTab
        read_only_fields = ["id"]
        fields = read_only_fields + [
            "type",
            "title",
            "description",
            "icon",
            "images",
        ]

    def validate_type(self, value: str):
        if self.instance and self.instance.type != value:
            raise ProjectTabChangeTypeError
        return value


class ProjectTabItemSerializer(serializers.ModelSerializer):
    images = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Image.objects.all(), required=False
    )

    class Meta:
        model = ProjectTabItem
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]
        fields = read_only_fields + [
            "title",
            "content",
            "images",
        ]
