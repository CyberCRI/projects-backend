import logging
import uuid
from types import SimpleNamespace
from typing import Dict, List, Union

from django.conf import settings
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.relations import SlugRelatedField

from apps.accounts.models import ProjectUser
from apps.commons.fields import HiddenPrimaryKeyRelatedField, UserMultipleIdRelatedField
from apps.commons.models import GroupData
from apps.commons.serializers import OrganizationRelatedSerializer
from apps.commons.utils import process_text
from apps.files.models import Image
from apps.files.serializers import ImageSerializer
from apps.projects.models import Project
from apps.skills.models import TagClassification
from apps.skills.serializers import (
    TagClassificationMultipleIdRelatedField,
    TagRelatedField,
)
from services.keycloak.serializers import IdentityProviderSerializer

from .exceptions import (
    CategoryHierarchyLoopError,
    DefaultTagClassificationIsNotEnabledError,
    FeaturedProjectPermissionDeniedError,
    NonRootCategoryParentError,
    OrganizationHierarchyLoopError,
    ParentCategoryOrganizationError,
    RootCategoryParentError,
)
from .models import Organization, ProjectCategory, Template

logger = logging.getLogger(__name__)


class OrganizationAddTeamMembersSerializer(serializers.Serializer):
    organization = HiddenPrimaryKeyRelatedField(
        required=False, write_only=True, queryset=Organization.objects.all()
    )
    admins = UserMultipleIdRelatedField(
        many=True, write_only=True, required=False, queryset=ProjectUser.objects.all()
    )
    facilitators = UserMultipleIdRelatedField(
        many=True, write_only=True, required=False, queryset=ProjectUser.objects.all()
    )
    users = UserMultipleIdRelatedField(
        many=True, write_only=True, required=False, queryset=ProjectUser.objects.all()
    )

    def create(self, validated_data):
        organization = validated_data["organization"]
        for role in GroupData.organization_roles():
            users = validated_data.get(role, [])
            group = getattr(organization, f"get_{role}")()
            for user in users:
                user.groups.remove(*organization.groups.filter(users=user))
                user.groups.add(group)
        return validated_data


class OrganizationRemoveTeamMembersSerializer(serializers.Serializer):
    organization = HiddenPrimaryKeyRelatedField(
        required=False, write_only=True, queryset=Organization.objects.all()
    )
    users = UserMultipleIdRelatedField(
        many=True, write_only=True, required=False, queryset=ProjectUser.objects.all()
    )

    def create(self, validated_data):
        organization = validated_data["organization"]
        users = validated_data.get("users", [])
        for user in users:
            user.groups.remove(*organization.groups.filter(users=user))
        return validated_data


class OrganizationAddFeaturedProjectsSerializer(serializers.Serializer):
    organization = HiddenPrimaryKeyRelatedField(
        required=False, write_only=True, queryset=Organization.objects.all()
    )
    featured_projects_ids = serializers.PrimaryKeyRelatedField(
        many=True, write_only=True, required=False, queryset=Project.objects.all()
    )

    def validate_featured_projects_ids(self, projects: List[Project]) -> List[Project]:
        request = self.context.get("request")
        if not all(request.user.can_see_project(project) for project in projects):
            raise FeaturedProjectPermissionDeniedError
        return projects

    def create(self, validated_data):
        organization = validated_data["organization"]
        projects_ids = validated_data.get("featured_projects_ids", [])
        projects = Project.objects.filter(
            id__in=[project.id for project in projects_ids]
        )
        organization.featured_projects.add(*projects)
        return validated_data


class OrganizationRemoveFeaturedProjectsSerializer(serializers.Serializer):
    organization = HiddenPrimaryKeyRelatedField(
        write_only=True, queryset=Organization.objects.all()
    )
    featured_projects_ids = serializers.PrimaryKeyRelatedField(
        many=True, write_only=True, required=False, queryset=Project.objects.all()
    )

    def create(self, validated_data):
        organization = validated_data["organization"]
        projects_ids = validated_data.get("featured_projects_ids", [])
        projects = Project.objects.filter(
            id__in=[project.id for project in projects_ids]
        )
        organization.featured_projects.remove(*projects)
        return validated_data


class OrganizationSerializer(OrganizationRelatedSerializer):
    parent_code = SlugRelatedField(
        many=False,
        required=False,
        queryset=Organization.objects.all(),
        source="parent",
        slug_field="code",
    )
    enabled_projects_tag_classifications = TagClassificationMultipleIdRelatedField(
        many=True, required=False
    )
    enabled_skills_tag_classifications = TagClassificationMultipleIdRelatedField(
        many=True, required=False
    )
    default_projects_tag_classification = TagClassificationMultipleIdRelatedField(
        required=False
    )
    default_skills_tag_classification = TagClassificationMultipleIdRelatedField(
        required=False
    )
    default_projects_tags = TagRelatedField(many=True, required=False)
    default_skills_tags = TagRelatedField(many=True, required=False)
    # read_only
    banner_image = ImageSerializer(read_only=True)
    logo_image = ImageSerializer(read_only=True)
    identity_providers = IdentityProviderSerializer(many=True, read_only=True)
    google_sync_enabled = serializers.SerializerMethodField()
    children = SlugRelatedField(
        many=True,
        read_only=True,
        slug_field="code",
    )
    # write_only
    banner_image_id = serializers.PrimaryKeyRelatedField(
        write_only=True,
        queryset=Image.objects.all(),
        source="banner_image",
        required=False,
    )
    logo_image_id = serializers.PrimaryKeyRelatedField(
        write_only=True, queryset=Image.objects.all(), source="logo_image"
    )
    team = OrganizationAddTeamMembersSerializer(required=False, write_only=True)

    class Meta:
        model = Organization
        fields = [
            "id",
            "code",
            "name",
            "parent_code",
            "contact_email",
            "dashboard_title",
            "dashboard_subtitle",
            "description",
            "chat_url",
            "chat_button_text",
            "languages",
            "language",
            "is_logo_visible_on_parent_dashboard",
            "background_color",
            "access_request_enabled",
            "onboarding_enabled",
            "force_login_form_display",
            "website_url",
            "created_at",
            "updated_at",
            "enabled_projects_tag_classifications",
            "enabled_skills_tag_classifications",
            "default_projects_tag_classification",
            "default_skills_tag_classification",
            "default_projects_tags",
            "default_skills_tags",
            # read_only
            "banner_image",
            "logo_image",
            "children",
            "google_sync_enabled",
            "identity_providers",
            # write_only
            "banner_image_id",
            "logo_image_id",
            "team",
        ]

    def validate_parent_code(self, value: Organization) -> Organization:
        if not self.instance:
            return value
        parent = value
        while parent is not None:
            if self.instance == parent:
                raise OrganizationHierarchyLoopError
            parent = parent.parent
        return value

    def _validate_default_tag_classification(
        self, value: TagClassification, field_name: str
    ) -> TagClassification:
        if not self.instance or field_name in self.initial_data:
            enabled_tag_classifications = self.initial_data.get(field_name, [])
            enabled_tag_classifications = TagClassification.objects.filter(
                Q(id__in=enabled_tag_classifications)
                | Q(slug__in=enabled_tag_classifications)
            ).distinct()
        elif self.instance:
            enabled_tag_classifications = getattr(self.instance, field_name).all()
        if value and value not in enabled_tag_classifications:
            raise DefaultTagClassificationIsNotEnabledError
        return value

    def validate_default_projects_tag_classification(
        self, value: TagClassification
    ) -> TagClassification:
        return self._validate_default_tag_classification(
            value, "enabled_projects_tag_classifications"
        )

    def validate_default_skills_tag_classification(
        self, value: TagClassification
    ) -> TagClassification:
        return self._validate_default_tag_classification(
            value, "enabled_skills_tag_classifications"
        )

    def get_related_organizations(self) -> Organization:
        # We're not supposed to be here since only super admin can create
        # organization and this function should not be called in this case.
        # see the view and permissions associated with this serializer.
        #
        # We return a dummy value so that the permission process can continue
        # and return a `False`.
        return [SimpleNamespace(code=uuid.uuid4(), pk=uuid.uuid4())]

    def get_google_sync_enabled(self, organization: Organization) -> bool:
        return organization.code == settings.GOOGLE_SYNCED_ORGANIZATION

    def create(self, validated_data):
        team = validated_data.pop("team", {})
        organization = super(OrganizationSerializer, self).create(validated_data)
        OrganizationAddTeamMembersSerializer().create(
            {"organization": organization, **team}
        )
        return organization

    def update(self, instance, validated_data):
        validated_data.pop("team", {})
        return super(OrganizationSerializer, self).update(instance, validated_data)


class OrganizationLightSerializer(OrganizationRelatedSerializer):
    logo_image = ImageSerializer(read_only=True)

    class Meta:
        model = Organization
        fields = [
            "id",
            "code",
            "is_logo_visible_on_parent_dashboard",
            "background_color",
            "website_url",
            "name",
            # read_only
            "logo_image",
            "is_logo_visible_on_parent_dashboard",
        ]

    def get_related_organizations(self) -> Organization:
        # We're not supposed to be here since only super admin can create
        # organization and this function should not be called in this case.
        # see the view and permissions associated with this serializer.
        #
        # We return a dummy value so that the permission process can continue
        # and return a `False`.
        return [SimpleNamespace(code=uuid.uuid4(), pk=uuid.uuid4())]

    def create(self, validated_data):
        """Create the instance's permissions and default groups."""
        organization = super().create(validated_data)
        organization.setup_permissions(self.context["request"].user)
        return organization


class TemplateLightSerializer(OrganizationRelatedSerializer):
    organization = SlugRelatedField(read_only=True, slug_field="code")

    class Meta:
        model = Template
        fields = [
            "id",
            "name",
            "description",
            "language",
            "organization",
        ]

    def get_related_organizations(self) -> List[Organization]:
        return [self.instance.organization] if self.instance else []


class ProjectCategoryLightSerializer(OrganizationRelatedSerializer):
    organization = SlugRelatedField(read_only=True, slug_field="code")

    class Meta:
        model = ProjectCategory
        fields = [
            "id",
            "slug",
            "name",
            "background_color",
            "foreground_color",
            "organization",
            "is_reviewable",
        ]

    def get_related_organizations(self) -> List[Organization]:
        self.is_valid(raise_exception=True)
        return [ProjectCategory.objects.get(id=self.validated_data["id"]).organization]


class ProjectTemplateSerializer(OrganizationRelatedSerializer):
    project_tags = TagRelatedField(many=True, read_only=True)

    class Meta:
        model = Template
        read_only_fields = [
            "id",
            "name",
            "description",
            "language",
            "project_title",
            "project_description",
            "project_tags",
            "blogentry_title",
            "blogentry_content",
            "goal_title",
            "goal_description",
            "review_title",
            "review_description",
            "audience",
            "time_estimation",
            "share_globally",
        ]
        fields = read_only_fields


class TemplateSerializer(OrganizationRelatedSerializer):
    project_tags = TagRelatedField(many=True, required=False)
    organization = SlugRelatedField(read_only=True, slug_field="code")
    categories = ProjectCategoryLightSerializer(many=True, read_only=True)
    # write-only
    categories_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        required=False,
        write_only=True,
        queryset=ProjectCategory.objects.all(),
        source="categories",
    )

    class Meta:
        model = Template
        read_only_fields = ["id", "organization", "categories"]
        fields = read_only_fields + [
            "name",
            "description",
            "language",
            "project_title",
            "project_description",
            "project_tags",
            "blogentry_title",
            "blogentry_content",
            "goal_title",
            "goal_description",
            "review_title",
            "review_description",
            "audience",
            "time_estimation",
            "share_globally",
            "categories_ids",
        ]

    def save(self, **kwargs):
        if not self.instance:
            super().save(**kwargs)
        for field in [
            "description",
            "project_description",
            "blogentry_content",
            "goal_description",
            "review_description",
        ]:
            text, images = process_text(
                request=self.context["request"],
                instance=self.instance,
                text=self.validated_data[field],
                upload_to="template/images/",
                view="Template-images-detail",
                organization_code=self.instance.organization.code,
                template_id=self.instance.id,
            )
            self.validated_data[field] = text
            self.instance.images.add(*images)
        return super().save(**kwargs)

    def get_related_organizations(self) -> List[Organization]:
        """Retrieve the related organizations"""
        return [self.validated_data.get("organization", [])]


class ProjectCategorySerializer(
    OrganizationRelatedSerializer, serializers.ModelSerializer
):
    parent = serializers.PrimaryKeyRelatedField(
        queryset=ProjectCategory.objects.all(),
        required=False,
        allow_null=True,
        write_only=True,
    )
    tags = TagRelatedField(many=True, required=False)
    # read-only
    templates = TemplateLightSerializer(many=True, read_only=True)
    background_image = ImageSerializer(read_only=True)
    organization = SlugRelatedField(read_only=True, slug_field="code")
    hierarchy = serializers.SerializerMethodField()
    children = serializers.SerializerMethodField()
    projects_count = serializers.SerializerMethodField()
    # write-only
    background_image_id = serializers.PrimaryKeyRelatedField(
        write_only=True,
        queryset=Image.objects.all(),
        source="background_image",
        required=False,
    )
    templates_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        required=False,
        write_only=True,
        queryset=Template.objects.all(),
        source="templates",
    )

    class Meta:
        model = ProjectCategory
        read_only_fields = ["slug", "organization", "background_image", "templates"]
        fields = read_only_fields + [
            "id",
            "name",
            "description",
            "background_color",
            "foreground_color",
            "is_reviewable",
            "order_index",
            "template",
            "only_reviewer_can_publish",
            "parent",
            "hierarchy",
            "children",
            "projects_count",
            "tags",
            # write-only
            "background_image_id",
            "templates_ids",
        ]

    def get_hierarchy(self, obj: ProjectCategory) -> List[Dict[str, Union[str, int]]]:
        hierarchy = []
        while obj.parent and not obj.parent.is_root:
            obj = obj.parent
            hierarchy.append({"id": obj.id, "slug": obj.slug, "name": obj.name})
        return [{"order": i, **h} for i, h in enumerate(hierarchy[::-1])]

    def get_children(self, obj: ProjectCategory) -> List[Dict[str, Union[str, int]]]:
        return [
            {
                "id": child.id,
                "slug": child.slug,
                "name": child.name,
            }
            for child in obj.children.all().order_by("name")
        ]

    def get_projects_count(self, obj: ProjectCategory) -> int:
        return obj.projects.count()

    def get_related_organizations(self) -> List[Organization]:
        """Retrieve the related organizations"""
        if "organization" in self.validated_data:
            return [self.validated_data["organization"]]
        return []

    def validate_parent(self, value):
        organization_code = (
            self.initial_data["organization_code"]
            if not self.instance
            else self.instance.organization.code
        )
        if (not value and not self.instance) or (
            not value and self.instance and not self.instance.is_root
        ):
            organization = get_object_or_404(Organization, code=organization_code)
            value = ProjectCategory.update_or_create_root(organization)
        if value and self.instance and self.instance.is_root is True:
            raise RootCategoryParentError
        if not value and self.instance and self.instance.is_root is False:
            raise NonRootCategoryParentError
        if value and value.organization.code != organization_code:
            raise ParentCategoryOrganizationError
        parent = value
        while parent is not None:
            if self.instance == parent:
                raise CategoryHierarchyLoopError
            parent = parent.parent
        return value
