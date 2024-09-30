import logging
import uuid
from types import SimpleNamespace
from typing import Dict, List, Union

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.relations import SlugRelatedField

from apps.accounts.models import ProjectUser
from apps.commons.fields import HiddenPrimaryKeyRelatedField, UserMultipleIdRelatedField
from apps.commons.serializers import OrganizationRelatedSerializer
from apps.commons.utils import process_text
from apps.files.models import Image
from apps.files.serializers import ImageSerializer
from apps.projects.models import Project
from apps.skills.serializers import TagRelatedField, TagSerializer
from services.keycloak.serializers import IdentityProviderSerializer

from .exceptions import (
    CategoryHierarchyLoopError,
    FeaturedProjectPermissionDeniedError,
    NonRootCategoryParentError,
    OrganizationHierarchyLoopError,
    ParentCategoryOrganizationError,
    RootCategoryParentError,
)
from .models import Faq, Organization, ProjectCategory, Template

logger = logging.getLogger(__name__)


class FaqSerializer(OrganizationRelatedSerializer):
    images = ImageSerializer(many=True, read_only=True)
    organization_code = serializers.SlugRelatedField(
        write_only=True,
        slug_field="code",
        source="organization",
        queryset=Organization.objects.all(),
    )
    images_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        write_only=True,
        queryset=Image.objects.all(),
        source="images",
        required=False,
    )

    class Meta:
        model = Faq
        fields = [
            "id",
            "title",
            "content",
            # read only
            "images",
            # write only
            "organization_code",
            "images_ids",
        ]

    def get_related_organizations(self) -> List[Organization]:
        """Retrieve the related organizations"""
        if "organization" in self.validated_data:
            return [self.validated_data["organization"]]
        return []

    @transaction.atomic
    def save(self, **kwargs):
        if "content" in self.validated_data:
            if not self.instance:
                super(FaqSerializer, self).save(**kwargs)
            text, images = process_text(
                self.context["request"],
                self.instance,
                self.validated_data["content"],
                "faq/images/",
                "Faq-images-detail",
                organization_code=self.instance.organization.code,
            )
            self.validated_data["content"] = text
            self.validated_data["images"] = images + [
                image for image in self.instance.images.all()
            ]
        return super(FaqSerializer, self).save(**kwargs)


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
        for role in Organization.DefaultGroup:
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
    # read_only
    banner_image = ImageSerializer(read_only=True)
    logo_image = ImageSerializer(read_only=True)
    faq = FaqSerializer(many=False, read_only=True)
    tags = TagSerializer(many=True, read_only=True, source="tags")
    children = SlugRelatedField(
        many=True,
        read_only=True,
        slug_field="code",
    )
    parent_code = SlugRelatedField(
        many=False,
        required=False,
        queryset=Organization.objects.all(),
        source="parent",
        slug_field="code",
    )
    identity_providers = IdentityProviderSerializer(many=True, read_only=True)
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
    tags_ids = TagRelatedField(
        many=True, write_only=True, source="tags", required=False
    )
    dashboard_title = serializers.CharField(required=True)
    dashboard_subtitle = serializers.CharField(required=True)
    google_sync_enabled = serializers.SerializerMethodField()
    team = OrganizationAddTeamMembersSerializer(required=False, write_only=True)

    class Meta:
        model = Organization
        fields = [
            "id",
            "background_color",
            "code",
            "contact_email",
            "dashboard_title",
            "dashboard_subtitle",
            "description",
            "chat_url",
            "chat_button_text",
            "language",
            "is_logo_visible_on_parent_dashboard",
            "access_request_enabled",
            "onboarding_enabled",
            "force_login_form_display",
            "name",
            "website_url",
            "created_at",
            "updated_at",
            # read_only
            "banner_image",
            "logo_image",
            "faq",
            "tags",
            "tags",
            "children",
            "parent_code",
            "is_logo_visible_on_parent_dashboard",
            "google_sync_enabled",
            "identity_providers",
            # write_only
            "banner_image_id",
            "logo_image_id",
            "tags_ids",
            "team",
        ]

    def validate_parent_code(self, value):
        if not self.instance:
            return value
        parent = value
        while parent is not None:
            if self.instance == parent:
                raise OrganizationHierarchyLoopError
            parent = parent.parent
        return value

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


class TemplateSerializer(OrganizationRelatedSerializer):
    images = ImageSerializer(many=True, read_only=True)
    images_ids = serializers.PrimaryKeyRelatedField(
        many=True,
        write_only=True,
        queryset=Image.objects.all(),
        source="images",
        required=False,
    )

    class Meta:
        model = Template
        fields = [
            "id",
            "title_placeholder",
            "goal_placeholder",
            "description_placeholder",
            "blogentry_placeholder",
            "blogentry_title_placeholder",
            "goal_title",
            "goal_description",
            "language",
            # read-only
            "images",
            # write-only
            "images_ids",
        ]

    def save(self, **kwargs):
        language = self.get_related_organizations().first().language
        return super().save(language=language, **kwargs)

    def get_related_organizations(self) -> List[Organization]:
        """Retrieve the related organizations"""
        return Organization.objects.filter(
            project_categories=self.validated_data["project_category"]
        )


class ProjectCategorySerializer(
    OrganizationRelatedSerializer, serializers.ModelSerializer
):
    tags = TagSerializer(many=True, read_only=True)
    template = TemplateSerializer(required=False, allow_null=True, default=None)
    parent = serializers.PrimaryKeyRelatedField(
        queryset=ProjectCategory.objects.all(),
        required=False,
        allow_null=True,
        write_only=True,
    )
    # read-only
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
    organization_code = serializers.SlugRelatedField(
        write_only=True,
        slug_field="code",
        source="organization",
        queryset=Organization.objects.all(),
    )
    tags_ids = TagRelatedField(
        many=True, write_only=True, source="tags", required=False
    )

    class Meta:
        model = ProjectCategory
        fields = [
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
            # read-only
            "background_image",
            "organization",
            "tags",
            # write-only
            "background_image_id",
            "organization_code",
            "tags_ids",
        ]

    def get_hierarchy(self, obj: ProjectCategory) -> List[Dict[str, Union[str, int]]]:
        hierarchy = []
        while obj.parent and not obj.parent.is_root:
            obj = obj.parent
            hierarchy.append({"id": obj.id, "name": obj.name})
        return [{"order": i, **h} for i, h in enumerate(hierarchy[::-1])]

    def get_children(self, obj: ProjectCategory) -> List[Dict[str, Union[str, int]]]:
        return [
            {"id": child.id, "name": child.name}
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

    @transaction.atomic
    def save(self, **kwargs):
        images = []
        if self.validated_data.get("template") and self.validated_data["template"].get(
            "description_placeholder"
        ):
            if not self.instance or not self.instance.template:
                super(ProjectCategorySerializer, self).save(**kwargs)
            text, description_images = process_text(
                self.context["request"],
                self.instance.template,
                self.validated_data["template"]["description_placeholder"],
                "template/images/",
                "Template-images-detail",
                category_id=self.instance.id,
            )
            self.validated_data["template"]["description_placeholder"] = text
            images += description_images
        if self.validated_data.get("template") and self.validated_data["template"].get(
            "blogentry_placeholder"
        ):
            if not self.instance or not self.instance.template:
                super(ProjectCategorySerializer, self).save(**kwargs)
            text, blog_images = process_text(
                self.context["request"],
                self.instance.template,
                self.validated_data["template"]["blogentry_placeholder"],
                "template/images/",
                "Template-images-detail",
                category_id=self.instance.id,
            )
            self.validated_data["template"]["blogentry_placeholder"] = text
            images += blog_images
        for image in images:
            self.instance.template.images.add(image)
        return super(ProjectCategorySerializer, self).save(**kwargs)

    @transaction.atomic
    def create(self, validated_data: Dict) -> ProjectCategory:
        if validated_data.get("template", None):
            validated_data["template"] = Template.objects.create(
                **validated_data["template"]
            )
        else:
            validated_data["template"] = Template.objects.create()
        return super().create(validated_data)

    @transaction.atomic
    def update(
        self, instance: ProjectCategory, validated_data: Dict
    ) -> ProjectCategory:
        if "template" in validated_data:
            if validated_data["template"] is None:
                instance.template = Template(id=instance.template_id)
            else:
                for attr, value in validated_data["template"].items():
                    setattr(instance.template, attr, value)
            instance.template.save()
            validated_data.pop("template")
        return super().update(instance, validated_data)


class ProjectCategoryLightSerializer(OrganizationRelatedSerializer):
    projects_count = serializers.SerializerMethodField()

    class Meta:
        model = ProjectCategory
        fields = [
            "id",
            "name",
            "background_color",
            "foreground_color",
            "projects_count",
        ]

    def get_projects_count(self, obj: ProjectCategory) -> int:
        return obj.projects.count()

    def get_related_organizations(self) -> List[Organization]:
        self.is_valid(raise_exception=True)
        return [ProjectCategory.objects.get(id=self.validated_data["id"]).organization]
