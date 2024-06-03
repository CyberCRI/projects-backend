import uuid
from typing import Dict, List, Optional, Union

from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers

from apps.commons.fields import (
    HiddenPrimaryKeyRelatedField,
    PrivacySettingProtectedCharField,
    PrivacySettingProtectedEmailField,
    PrivacySettingProtectedMethodField,
    UserMultipleIdRelatedField,
)
from apps.files.models import Image
from apps.files.serializers import ImageSerializer
from apps.misc.serializers import TagRelatedField
from apps.notifications.models import Notification
from apps.organizations.models import Organization
from apps.projects.models import Project

from .exceptions import (
    FeaturedProjectPermissionDeniedError,
    GroupHierarchyLoopError,
    GroupOrganizationChangeError,
    NonRootGroupParentError,
    ParentGroupOrganizationError,
    RootGroupParentError,
    UserRoleAssignmentError,
    UserRolePermissionDeniedError,
)
from .models import AnonymousUser, PeopleGroup, PrivacySettings, ProjectUser, Skill
from .utils import get_default_group, get_instance_from_group


class PrivacySettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrivacySettings
        fields = (
            "publication_status",
            "profile_picture",
            "skills",
            "mobile_phone",
            "personal_email",
            "socials",
        )


class UserAdminListSerializer(serializers.ModelSerializer):
    current_org_role = serializers.CharField(required=False, read_only=True)
    email_verified = serializers.BooleanField(required=False, read_only=True)
    people_groups = serializers.SerializerMethodField()

    class Meta:
        model = ProjectUser
        read_only_fields = [
            "id",
            "slug",
            "keycloak_id",
            "email",
            "given_name",
            "family_name",
            "job",
            "current_org_role",
            "email_verified",
            "last_login",
            "people_groups",
            "created_at",
        ]
        fields = read_only_fields

    def get_people_groups(self, user: ProjectUser) -> list:
        queryset = PeopleGroup.objects.filter(groups__users=user).distinct()
        return PeopleGroupSuperLightSerializer(
            queryset, many=True, context=self.context
        ).data


class UserLightSerializer(serializers.ModelSerializer):
    pronouns = serializers.CharField(required=False)
    profile_picture = PrivacySettingProtectedMethodField(
        privacy_field="profile_picture"
    )
    current_org_role = serializers.CharField(required=False, read_only=True)
    is_manager = serializers.BooleanField(required=False, read_only=True)
    is_leader = serializers.BooleanField(required=False, read_only=True)
    people_groups = serializers.SerializerMethodField()
    skills = PrivacySettingProtectedMethodField(
        privacy_field="skills", default_value=[]
    )

    class Meta:
        model = ProjectUser
        read_only_fields = [
            "id",
            "slug",
            "keycloak_id",
            "people_id",
            "email",
            "given_name",
            "family_name",
            "pronouns",
            "job",
            "profile_picture",
            "current_org_role",
            "is_manager",
            "is_leader",
            "last_login",
            "people_groups",
            "created_at",
            "skills",
        ]
        fields = read_only_fields

    def to_representation(self, instance):
        request = self.context.get("request", None)
        if request and request.user.get_user_queryset().filter(id=instance.id).exists():
            return super().to_representation(instance)
        return {
            **AnonymousUser.serialize(with_permissions=False),
            "current_org_role": None,
            "is_manager": False,
            "is_leader": False,
        }

    def get_profile_picture(self, user: ProjectUser) -> Union[Dict, str]:
        if user.profile_picture is None:
            return None
        return ImageSerializer(user.profile_picture).data

    def get_people_groups(self, user: ProjectUser) -> list:
        request_user = getattr(
            self.context.get("request", None), "user", AnonymousUser()
        )
        queryset = (
            request_user.get_people_group_queryset()
            .filter(groups__users=user)
            .distinct()
        )
        return PeopleGroupSuperLightSerializer(
            queryset, many=True, context=self.context
        ).data

    def get_skills(self, user: ProjectUser) -> List[Dict]:
        return SkillSerializer(
            user.skills.filter(type=Skill.SkillType.SKILL), many=True
        ).data


class PeopleGroupSuperLightSerializer(serializers.ModelSerializer):
    class Meta:
        model = PeopleGroup
        read_only_fields = ["id", "slug", "name"]
        fields = read_only_fields


class PeopleGroupLightSerializer(serializers.ModelSerializer):
    header_image = ImageSerializer(read_only=True)
    members_count = serializers.SerializerMethodField()
    roles = serializers.SlugRelatedField(
        many=True,
        slug_field="name",
        read_only=True,
        source="groups",
    )
    organization = serializers.SlugRelatedField(read_only=True, slug_field="code")

    def get_members_count(self, group: PeopleGroup) -> int:
        return group.get_all_members().count()

    class Meta:
        model = PeopleGroup
        read_only_fields = ["organization", "is_root", "publication_status"]
        fields = read_only_fields + [
            "id",
            "slug",
            "name",
            "description",
            "short_description",
            "email",
            "header_image",
            "members_count",
            "roles",
        ]


class PeopleGroupAddTeamMembersSerializer(serializers.Serializer):
    people_group = HiddenPrimaryKeyRelatedField(
        required=False, write_only=True, queryset=PeopleGroup.objects.all()
    )
    leaders = UserMultipleIdRelatedField(
        many=True, write_only=True, required=False, queryset=ProjectUser.objects.all()
    )
    managers = UserMultipleIdRelatedField(
        many=True, write_only=True, required=False, queryset=ProjectUser.objects.all()
    )
    members = UserMultipleIdRelatedField(
        many=True, write_only=True, required=False, queryset=ProjectUser.objects.all()
    )

    def create(self, validated_data):
        people_group = validated_data["people_group"]
        for role in PeopleGroup.DefaultGroup:
            users = validated_data.get(role, [])
            group = getattr(people_group, f"get_{role}")()
            for user in users:
                user.groups.remove(*people_group.groups.filter(users=user))
                user.groups.add(group)
        return validated_data


class PeopleGroupRemoveTeamMembersSerializer(serializers.Serializer):
    people_group = HiddenPrimaryKeyRelatedField(
        write_only=True, queryset=PeopleGroup.objects.all()
    )
    users = UserMultipleIdRelatedField(
        many=True, write_only=True, required=False, queryset=ProjectUser.objects.all()
    )

    def create(self, validated_data):
        people_group = validated_data["people_group"]
        users = validated_data.get("users", [])
        for user in users:
            user.groups.remove(*people_group.groups.filter(users=user))
        return validated_data


class PeopleGroupAddFeaturedProjectsSerializer(serializers.Serializer):
    people_group = HiddenPrimaryKeyRelatedField(
        required=False, write_only=True, queryset=PeopleGroup.objects.all()
    )
    featured_projects = serializers.PrimaryKeyRelatedField(
        many=True, write_only=True, required=False, queryset=Project.objects.all()
    )

    def validate_featured_projects(self, projects: List[Project]) -> List[Project]:
        request = self.context.get("request")
        if not all(request.user.can_see_project(project) for project in projects):
            raise FeaturedProjectPermissionDeniedError
        return projects

    def create(self, validated_data):
        people_group = validated_data["people_group"]
        projects = validated_data.get("featured_projects", [])
        people_group.featured_projects.add(*projects)
        return validated_data


class PeopleGroupRemoveFeaturedProjectsSerializer(serializers.Serializer):
    people_group = HiddenPrimaryKeyRelatedField(
        write_only=True, queryset=PeopleGroup.objects.all()
    )
    featured_projects = serializers.PrimaryKeyRelatedField(
        many=True, write_only=True, required=False, queryset=Project.objects.all()
    )

    def create(self, validated_data):
        people_group = validated_data["people_group"]
        projects = validated_data.get("featured_projects", [])
        people_group.featured_projects.remove(*projects)
        return validated_data


class PeopleGroupSerializer(serializers.ModelSerializer):
    organization = serializers.SlugRelatedField(
        slug_field="code", queryset=Organization.objects.all()
    )
    hierarchy = serializers.SerializerMethodField()
    children = serializers.SerializerMethodField()
    parent = serializers.PrimaryKeyRelatedField(
        queryset=PeopleGroup.objects.all(),
        required=False,
        allow_null=True,
        write_only=True,
    )
    header_image = ImageSerializer(read_only=True)
    logo_image = ImageSerializer(read_only=True)
    roles = serializers.SlugRelatedField(
        many=True,
        slug_field="name",
        read_only=True,
        source="groups",
    )
    team = PeopleGroupAddTeamMembersSerializer(required=False, write_only=True)
    featured_projects = serializers.PrimaryKeyRelatedField(
        many=True, write_only=True, required=False, queryset=Project.objects.all()
    )

    def get_hierarchy(self, obj: PeopleGroup) -> List[Dict[str, Union[str, int]]]:
        hierarchy = []
        while obj.parent and not obj.parent.is_root:
            obj = obj.parent
            hierarchy.append({"id": obj.id, "slug": obj.slug, "name": obj.name})
        return [{"order": i, **h} for i, h in enumerate(hierarchy[::-1])]

    def get_children(self, obj: PeopleGroup) -> List[Dict[str, Union[str, int]]]:
        return [
            {"id": child.id, "name": child.name}
            for child in obj.children.all().order_by("name")
        ]

    def validate_featured_projects(self, projects: List[Project]) -> List[Project]:
        request = self.context.get("request")
        if not all(request.user.can_see_project(project) for project in projects):
            raise FeaturedProjectPermissionDeniedError
        return projects

    def validate_organization(self, value):
        if self.instance and self.instance.organization != value:
            raise GroupOrganizationChangeError
        return value

    def run_validation(self, data=serializers.empty):
        data["parent"] = (
            data.get("parent", self.instance.parent)
            if self.instance
            else data.get("parent", None)
        )
        return super().run_validation(data)

    def validate_parent(self, value):
        organization_code = (
            self.initial_data["organization"]
            if not self.instance
            else self.instance.organization.code
        )
        if (not value and not self.instance) or (
            not value and self.instance and not self.instance.is_root
        ):
            organization = get_object_or_404(Organization, code=organization_code)
            value = PeopleGroup.update_or_create_root(organization)
        if value and self.instance and self.instance.is_root is True:
            raise RootGroupParentError
        if not value and self.instance and self.instance.is_root is False:
            raise NonRootGroupParentError
        if value and value.organization.code != organization_code:
            raise ParentGroupOrganizationError
        parent = value
        while parent is not None:
            if self.instance == parent:
                raise GroupHierarchyLoopError
            parent = parent.parent
        return value

    def create(self, validated_data):
        team = validated_data.pop("team", {})
        featured_projects = validated_data.pop("featured_projects", [])
        people_group = super(PeopleGroupSerializer, self).create(validated_data)
        PeopleGroupAddTeamMembersSerializer().create(
            {"people_group": people_group, **team}
        )
        PeopleGroupAddFeaturedProjectsSerializer().create(
            {"people_group": people_group, "featured_projects": featured_projects}
        )
        return people_group

    def update(self, instance, validated_data):
        validated_data.pop("team", {})
        validated_data.pop("featured_projects", [])
        return super(PeopleGroupSerializer, self).update(instance, validated_data)

    def save(self, **kwargs):
        return super().save(**kwargs)

    class Meta:
        model = PeopleGroup
        read_only_fields = ["is_root", "slug"]
        fields = read_only_fields + [
            "id",
            "name",
            "description",
            "short_description",
            "email",
            "parent",
            "organization",
            "hierarchy",
            "children",
            "header_image",
            "logo_image",
            "roles",
            "publication_status",
            "team",
            "featured_projects",
        ]


@extend_schema_serializer(exclude_fields=("roles",))
class UserSerializer(serializers.ModelSerializer):
    sdgs = serializers.ListField(
        child=serializers.IntegerField(min_value=1, max_value=17),
        required=False,
    )
    roles = serializers.SlugRelatedField(
        many=True,
        queryset=Group.objects.all(),
        slug_field="name",
        required=False,
        source="groups",
    )
    roles_to_add = serializers.SlugRelatedField(
        many=True,
        write_only=True,
        queryset=Group.objects.all(),
        slug_field="name",
        required=False,
        source="groups",
    )
    roles_to_remove = serializers.SlugRelatedField(
        many=True,
        write_only=True,
        queryset=Group.objects.all(),
        slug_field="name",
        required=False,
        source="groups",
    )

    # Read only fields
    permissions = serializers.SerializerMethodField()
    people_groups = serializers.SerializerMethodField()
    notifications = serializers.SerializerMethodField()
    privacy_settings = PrivacySettingsSerializer(read_only=True)

    # Privacy protected fields
    skills = PrivacySettingProtectedMethodField(
        privacy_field="skills", default_value=[]
    )
    hobbies = PrivacySettingProtectedMethodField(
        privacy_field="skills", default_value=[]
    )
    profile_picture = PrivacySettingProtectedMethodField(
        privacy_field="profile_picture"
    )
    mobile_phone = PrivacySettingProtectedCharField(
        privacy_field="mobile_phone", required=False, allow_blank=True
    )
    personal_email = PrivacySettingProtectedEmailField(
        privacy_field="personal_email", required=False, allow_blank=True
    )
    facebook = PrivacySettingProtectedCharField(
        privacy_field="socials", required=False, allow_blank=True
    )
    linkedin = PrivacySettingProtectedCharField(
        privacy_field="socials", required=False, allow_blank=True
    )
    medium = PrivacySettingProtectedCharField(
        privacy_field="socials", required=False, allow_blank=True
    )
    website = PrivacySettingProtectedCharField(
        privacy_field="socials", required=False, allow_blank=True
    )
    skype = PrivacySettingProtectedCharField(
        privacy_field="socials", required=False, allow_blank=True
    )
    landline_phone = PrivacySettingProtectedCharField(
        privacy_field="socials", required=False, allow_blank=True
    )
    twitter = PrivacySettingProtectedCharField(
        privacy_field="socials", required=False, allow_blank=True
    )

    # Write only profile picture fields
    profile_picture_file = serializers.ImageField(
        write_only=True, required=False, allow_null=True
    )
    profile_picture_scale_x = serializers.FloatField(
        write_only=True, required=False, allow_null=True
    )
    profile_picture_scale_y = serializers.FloatField(
        write_only=True, required=False, allow_null=True
    )
    profile_picture_left = serializers.FloatField(
        write_only=True, required=False, allow_null=True
    )
    profile_picture_top = serializers.FloatField(
        write_only=True, required=False, allow_null=True
    )
    profile_picture_natural_ratio = serializers.FloatField(
        write_only=True, required=False, allow_null=True
    )

    class Meta:
        model = ProjectUser
        read_only_fields = ["id", "slug", "created_at"]
        fields = read_only_fields + [
            "roles",
            "roles_to_add",
            "roles_to_remove",
            "permissions",
            "is_superuser",
            "people_groups",
            "notifications",
            "privacy_settings",
            "skills",
            "hobbies",
            "profile_picture",
            "id",
            "language",
            "onboarding_status",
            "keycloak_id",
            "people_id",
            "email",
            "given_name",
            "family_name",
            "birthdate",
            "pronouns",
            "personal_description",
            "short_description",
            "professional_description",
            "location",
            "job",
            "mobile_phone",
            "personal_email",
            "sdgs",
            "facebook",
            "linkedin",
            "medium",
            "website",
            "skype",
            "landline_phone",
            "twitter",
            "profile_picture_file",
            "profile_picture_scale_x",
            "profile_picture_scale_y",
            "profile_picture_left",
            "profile_picture_top",
            "profile_picture_natural_ratio",
        ]

    def to_representation(self, instance):
        request = self.context.get("request", None)
        if request and request.user.get_user_queryset().filter(id=instance.id).exists():
            return super().to_representation(instance)
        return {
            **AnonymousUser.serialize(with_permissions=False),
            "current_org_role": None,
            "is_manager": False,
            "is_leader": False,
        }

    def validate_roles(self, groups: List[Group]) -> List[Group]:
        request = self.context.get("request")
        user = request.user
        groups_to_add = (
            [group for group in groups if group not in self.instance.groups.all()]
            if self.instance
            else groups
        )
        groups_to_remove = (
            [group for group in self.instance.groups.all() if group not in groups]
            if self.instance
            else []
        )
        for group in groups_to_add + groups_to_remove:
            instance = get_instance_from_group(group)
            if not instance or (
                isinstance(instance, Project) and group.people_groups.exists()
            ):
                raise UserRoleAssignmentError(group.name)
            content_type = ContentType.objects.get_for_model(instance)
            if not any(
                [
                    user.has_perm(
                        f"{content_type.app_label}.change_{content_type.model}"
                    ),
                    user.has_perm(
                        f"{content_type.app_label}.change_{content_type.model}",
                        instance,
                    ),
                    *[
                        user.has_perm(
                            f"organizations.change_{content_type.model}", organization
                        )
                        for organization in instance.get_related_organizations()
                    ],
                ]
            ):
                raise UserRolePermissionDeniedError(group.name)
        default_group = get_default_group()
        if default_group not in groups:
            groups.append(default_group)
        return groups

    def get_permissions(self, user: ProjectUser) -> List[str]:
        return user.get_instance_permissions_representations()

    def get_skills(self, user: ProjectUser) -> List[Dict]:
        return SkillSerializer(
            user.skills.filter(type=Skill.SkillType.SKILL), many=True
        ).data

    def get_hobbies(self, user: ProjectUser) -> List[Dict]:
        return SkillSerializer(
            user.skills.filter(type=Skill.SkillType.HOBBY), many=True
        ).data

    def get_profile_picture(self, user: ProjectUser) -> Optional[Dict]:
        if user.profile_picture is None:
            return None
        return ImageSerializer(user.profile_picture).data

    def get_people_groups(self, user: ProjectUser) -> list:
        request_user = getattr(
            self.context.get("request", None), "user", AnonymousUser()
        )
        queryset = (
            request_user.get_people_group_queryset()
            .filter(groups__users=user)
            .distinct()
        )
        return PeopleGroupSuperLightSerializer(
            queryset, many=True, context=self.context
        ).data

    def get_notifications(self, user: ProjectUser) -> int:
        return Notification.objects.filter(is_viewed=False, receiver=user).count()

    def create(self, validated_data):
        profile_picture = {
            "file": validated_data.pop("profile_picture_file", None),
            "scale_x": validated_data.pop("profile_picture_scale_x", None),
            "scale_y": validated_data.pop("profile_picture_scale_y", None),
            "left": validated_data.pop("profile_picture_left", None),
            "top": validated_data.pop("profile_picture_top", None),
            "natural_ratio": validated_data.pop("profile_picture_natural_ratio", None),
        }
        instance = super(UserSerializer, self).create(validated_data)
        if profile_picture["file"]:
            image = Image(
                name=profile_picture["file"].name,
                owner=instance,
                **profile_picture,
            )
            upload_to = f"account/profile/{uuid.uuid4()}#{image.name}"
            image._upload_to = lambda _, __: upload_to
            image.save()
            instance.profile_picture = image
            instance.save()
        return instance

    def to_internal_value(self, data):
        """
        Overriding this method to handle roles_to_add and roles_to_remove.

        Because UserViewSet needs to handle formdata and json, we use a custom parser
        located in apps/accounts/parsers.py. Otherwise this method would cause an
        error when trying to process data from a formdata.
        """

        # Put the profile_picture_file in the data dict
        data["profile_picture_file"] = data.pop("profile_picture_file", [None])[0]

        # Handle roles_to_add and roles_to_remove
        groups_to_add = data.pop("roles_to_add", [])
        groups_to_remove = data.pop("roles_to_remove", [])
        if self.instance:
            groups = self.instance.groups.exclude(name__in=groups_to_remove)
            for group in groups_to_add:
                group = Group.objects.get(name=group)
                group_instance = get_instance_from_group(group)
                if group_instance:
                    groups = groups.exclude(
                        name__in=group_instance.groups.values_list("name", flat=True)
                    )
                groups = Group.objects.filter(
                    name__in=[group.name, *groups.values_list("name", flat=True)]
                )
            data["roles"] = groups
        else:
            data["roles"] = Group.objects.filter(name__in=groups_to_add)

        # Get default language from organization if not provided
        organization_groups = Group.objects.filter(
            organizations__isnull=False,
            name__in=groups_to_add,
        )
        if organization_groups.exists() and "language" not in data.keys():
            group = organization_groups.first()
            organization = group.organizations.first()
            data["language"] = organization.language

        return super().to_internal_value(data)


class EmptyPayloadResponseSerializer(serializers.Serializer):
    detail = serializers.CharField()

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class SkillSerializer(serializers.ModelSerializer):
    user = UserMultipleIdRelatedField(queryset=ProjectUser.objects.all())
    wikipedia_tag = TagRelatedField()

    class Meta:
        model = Skill
        fields = [
            "id",
            "user",
            "wikipedia_tag",
            "level",
            "level_to_reach",
            "category",
            "type",
        ]


class CredentialsSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=255)
    password = serializers.CharField(max_length=255)


class AccessTokenSerializer(serializers.Serializer):
    access_token = serializers.CharField(max_length=2048)
    expires_in = serializers.IntegerField()
    refresh_expires_in = serializers.IntegerField()
    refresh_token = serializers.CharField(max_length=2048)
    token_type = serializers.CharField(max_length=255)
    session_state = serializers.CharField(max_length=255)
    scope = serializers.CharField(max_length=255)
