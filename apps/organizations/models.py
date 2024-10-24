from typing import TYPE_CHECKING, Iterable, List, Optional

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.aggregates import ArrayAgg
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.http import Http404
from guardian.shortcuts import assign_perm
from simple_history.models import HistoricalRecords

from apps.commons.models import Language, OrganizationRelated, PermissionsSetupModel
from apps.commons.utils import (
    get_permissions_from_subscopes,
    get_write_permissions_from_subscopes,
)

if TYPE_CHECKING:
    from apps.accounts.models import ProjectUser


class Faq(models.Model, OrganizationRelated):
    """Frequently asked question of an organization.

    title: CharField
        Name of the FAQ.
    content: TextField
        Content of the FAQ.
    images: ManyToManyField
        Images used by the FAQ.
    """

    title = models.CharField(max_length=255)
    images = models.ManyToManyField("files.Image", related_name="faqs")
    content = models.TextField(blank=True)

    def get_related_organizations(self) -> List["Organization"]:
        """Return the organization related to this model."""
        return [self.organization]


class Organization(PermissionsSetupModel, OrganizationRelated):
    """An Organization is a set of ProjectCategories contained in an OrganizationDirectory.

    Attributes
    ----------
    name: CharField
        Name of the organization.
    background_color: CharField
        RGBA hex code of the background color of the logo (include '#').
    banner_image: ForeignKey, optional
        Banner image shown on the organization's home page.
    logo_image: ForeignKey
        Logo of the organization.
    images: ManyToManyField
        Other images used by this organization.
    code: CharField
        Organization's code.
    dashboard_title: CharField, optional
        Title displayed on the dashboard.
    dashboard_subtitle: CharField, optional
        Subtitle displayed on the dashboard.
    description: TextField
        Description of the organization.
    contact_email: EmailField
        Contact email of the organization.
    chat_url: URLField
        Chat URL of the organization.
    language: CharField
        Main language of the organization.
    website_url: CharField
        Organization's website.
    faq: OneToOneField, optional
        The organization's frequently asked questions.
    is_logo_visible_on_parent_dashboard: BooleanField
        Whether to show or hide the organization's logo on the main
        organization's portal.
    tags: ManyToManyField
        Tags this organization is referred to.
    created_at: DateTimeField
        Date of creation of the organization.
    updated_at: DateTimeField
        Date of the last change made to the organization.
    parent: ForeignKey, optional
        Parent organization.
    groups: ManyToManyField
        Permission groups of the organization. Default groups are:
        - users
        - admins
        - facilitators
    access_request_enabled: BooleanField
        Whether access requests are enabled on the organization.
    onboarding_enabled: BooleanField
        Whether onboarding is enabled on the organization.
    identity_providers: ManyToManyField
        Identity providers authorized to access the organization.
    """

    class DefaultGroup(models.TextChoices):
        """Default permission groups of an organization."""

        USERS = "users"
        ADMINS = "admins"
        FACILITATORS = "facilitators"

    code = models.CharField(max_length=50, unique=True)
    website_url = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    dashboard_title = models.CharField(max_length=255)
    dashboard_subtitle = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    contact_email = models.EmailField(max_length=255, blank=True)
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        related_name="children",
        null=True,
        blank=True,
    )

    background_color = models.CharField(max_length=9, blank=True)
    chat_url = models.URLField(blank=True, max_length=255)
    chat_button_text = models.CharField(blank=True, max_length=255)
    language = models.CharField(
        max_length=2, choices=Language.choices, default=Language.default()
    )

    onboarding_enabled = models.BooleanField(default=True)
    is_logo_visible_on_parent_dashboard = models.BooleanField(default=True)
    access_request_enabled = models.BooleanField(default=True)
    force_login_form_display = models.BooleanField(default=False)

    banner_image = models.ForeignKey(
        "files.Image",
        on_delete=models.SET_NULL,
        null=True,
        related_name="organization_banner",
    )
    logo_image = models.ForeignKey(
        "files.Image",
        on_delete=models.PROTECT,
        related_name="organization_logo",
    )
    images = models.ManyToManyField(
        "files.Image", related_name="organizations", blank=True
    )

    faq = models.OneToOneField(
        Faq, on_delete=models.SET_NULL, null=True, related_name="organization"
    )
    identity_providers = models.ManyToManyField(
        "keycloak.IdentityProvider", related_name="organizations", blank=True
    )
    featured_projects = models.ManyToManyField(
        "projects.Project", related_name="org_featured_projects", blank=True
    )
    wikipedia_tags = models.ManyToManyField("misc.WikipediaTag", blank=True)
    default_projects_tags = models.ManyToManyField(
        "skills.Tag",
        related_name="default_organizations_projects",
        blank=True,
    )
    default_skills_tags = models.ManyToManyField(
        "skills.Tag",
        related_name="default_organizations_skills",
        blank=True,
    )
    enabled_projects_tag_classifications = models.ManyToManyField(
        "skills.TagClassification",
        related_name="enabled_organizations_projects",
        blank=True,
    )
    enabled_skills_tag_classifications = models.ManyToManyField(
        "skills.TagClassification",
        related_name="enabled_organizations_skills",
        blank=True,
    )
    default_projects_tag_classification = models.ForeignKey(
        "skills.TagClassification",
        related_name="default_organizations_projects",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    default_skills_tag_classification = models.ForeignKey(
        "skills.TagClassification",
        related_name="default_organizations_skills",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    groups = models.ManyToManyField(Group, related_name="organizations")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        subscopes = (
            ("project", "projects"),
            ("projectmessage", "project messages"),
            ("projectuser", "users"),
            ("peoplegroup", "groups"),
        )
        write_only_subscopes = (
            ("tag", "tags"),
            ("tagclassification", "tag classifications"),
            ("faq", "faqs"),
            ("projectcategory", "project categories"),
            ("review", "reviews"),
            ("comment", "comments"),
            ("follow", "follows"),
            ("invitation", "invitation links"),
            ("news", "news"),
            ("event", "event"),
            ("instruction", "instructions"),
        )
        permissions = (
            ("view_stat", "Can view stats"),
            ("view_org_project", "Can view community projects"),
            ("view_org_projectuser", "Can view community users"),
            ("view_org_peoplegroup", "Can view community groups"),
            ("lock_project", "Can lock and unlock a project"),
            ("duplicate_project", "Can duplicate a project"),
            ("change_locked_project", "Can update a locked project"),
            ("manage_accessrequest", "Can manage access requests"),
            *get_permissions_from_subscopes(subscopes),
            *get_write_permissions_from_subscopes(write_only_subscopes),
        )

    def __str__(self) -> str:
        return "%s object (%s)" % (self.__class__.__name__, self.code)

    @property
    def content_type(self):
        return ContentType.objects.get_for_model(Organization)

    def get_related_organizations(self) -> List["Organization"]:
        """Return the organization related to this model."""
        return [self]

    def get_default_admins_permissions(self) -> Iterable[Permission]:
        return Permission.objects.filter(content_type=self.content_type)

    def get_default_facilitators_permissions(self) -> Iterable[Permission]:
        excluded_permissions = [
            "manage_accessrequest",
            *[
                f"{action}_{subscope}"
                for action in ["change", "delete", "add"]
                for subscope in [
                    "tag",
                    "review",
                    "faq",
                    "projectcategory",
                    "tagclassification",
                ]
            ],
        ]
        return Permission.objects.filter(content_type=self.content_type).exclude(
            codename__in=excluded_permissions
        )

    def get_default_users_permissions(self) -> Iterable[Permission]:
        filtered_permissions = [
            "view_org_project",
            "view_org_projectuser",
            "view_org_peoplegroup",
            "add_project",
        ]
        return Permission.objects.filter(
            content_type=self.content_type,
            codename__in=filtered_permissions,
        )

    def setup_permissions(self, user: Optional["ProjectUser"] = None):
        """
        Create or update the default groups and permissions for the organization.
        """
        admins = self.get_admins()
        admins.permissions.clear()
        assign_perm("accounts.get_user_by_email", admins)
        # TODO: remove that when we have a better way to handle permissions
        assign_perm("accounts.add_projectuser", admins)
        assign_perm("accounts.change_projectuser", admins)
        assign_perm("accounts.delete_projectuser", admins)
        for permission in self.get_default_admins_permissions():
            assign_perm(permission, admins, self)

        facilitators = self.get_facilitators()
        facilitators.permissions.clear()
        for permission in self.get_default_facilitators_permissions():
            assign_perm(permission, facilitators, self)

        users = self.get_users()
        users.permissions.clear()
        for permission in self.get_default_users_permissions():
            assign_perm(permission, users, self)

        if user:
            admins.users.add(user)
        self.groups.add(admins, facilitators, users)
        self.permissions_up_to_date = True
        self.save(update_fields=["permissions_up_to_date"])

    def remove_duplicated_roles(self):
        """Remove duplicated roles in the group."""
        self.users.set(
            self.users.exclude(pk__in=self.admins.values_list("pk", flat=True)).exclude(
                pk__in=self.facilitators.values_list("pk", flat=True)
            )
        )
        self.facilitators.set(
            self.facilitators.exclude(pk__in=self.admins.values_list("pk", flat=True))
        )

    def get_or_create_group(self, name: str) -> Group:
        """Return the group with the given name."""
        group, created = Group.objects.get_or_create(
            name=f"{self.content_type.model}:#{self.pk}:{name}"
        )
        if created:
            self.groups.add(group)
        return group

    def get_admins(self) -> Group:
        """Return the admins group."""
        return self.get_or_create_group(self.DefaultGroup.ADMINS)

    def get_facilitators(self) -> Group:
        """Return the facilitators group."""
        return self.get_or_create_group(self.DefaultGroup.FACILITATORS)

    def get_users(self) -> Group:
        """Return the users group."""
        return self.get_or_create_group(self.DefaultGroup.USERS)

    @property
    def admins(self) -> List["ProjectUser"]:
        return self.get_admins().users

    @property
    def facilitators(self) -> List["ProjectUser"]:
        return self.get_facilitators().users

    @property
    def users(self) -> List["ProjectUser"]:
        return self.get_users().users

    def get_all_members(self) -> List["ProjectUser"]:
        """Return the all members."""
        return (
            self.admins.all() | self.facilitators.all() | self.users.all()
        ).distinct()


class Template(models.Model, OrganizationRelated):
    """Templates are used to guide the creation a new project by providing placeholders.

    Attributes
    ----------
    title_placeholder: CharField
        Placeholder used for the title of the project.
    description_placeholder: TextField
        Placeholder used for the description for the project.
    goal_placeholder: CharField
        Placeholder used for the goal of the project.
    blogentry_placeholder: TextField
        Placeholder used for the blog entry of the project.
    images: ManyToManyField
        Images used by the template.
    """

    title_placeholder = models.CharField(max_length=255, default="", blank=True)
    description_placeholder = models.TextField(default="", blank=True)
    goal_placeholder = models.CharField(max_length=255, default="", blank=True)
    blogentry_title_placeholder = models.TextField(
        max_length=255, default="", blank=True
    )
    blogentry_placeholder = models.TextField(default="", blank=True)
    images = models.ManyToManyField("files.Image", related_name="templates")
    goal_title = models.CharField(max_length=255, blank=True)
    goal_description = models.TextField(blank=True)
    language = models.CharField(
        max_length=2, choices=Language.choices, default=Language.default()
    )

    def get_related_organizations(self) -> Organization:
        try:
            return self.project_category.get_related_organization()
        except ObjectDoesNotExist:
            raise Http404()


class ProjectCategory(models.Model, OrganizationRelated):
    """A ProjectCategory is a container for projects of the same type.

    Type might be student projects, research project, etc...

    Attributes
    ----------
    name: CharField
        Name of the category.
    description: TextField
        Description of the category.
    background_color: CharField
        RGBA hex code of the color displayed behind the name of the category
        (include '#').
    foreground_color: CharField
        RGBA hex code of the text color for the name of the category
        (include '#').
    background_image: ForeignKey, optional
        Image used to illustrate the category.
    organization: ForeignKey
        Organization the category is a part of.
    is_reviewable: BooleanField
        Whether the category is reviewable or not.
    order_index: SmallIntegerField
        Position of the category in the list.
    tags: ManyToManyField
        Tags visible in the category.
    template: OneToOneField, optional
        Template used by the category.
    history: HistoricalRecords
        History of the object.
    """

    name = models.CharField(max_length=100, help_text="name of the category")
    description = models.TextField(blank=True, help_text="description of the category")
    background_color = models.CharField(blank=True, max_length=9)
    foreground_color = models.CharField(blank=True, max_length=9)
    background_image = models.ForeignKey(
        "files.Image",
        on_delete=models.SET_NULL,
        null=True,
        related_name="project_category",
    )
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="project_categories"
    )
    is_reviewable = models.BooleanField(default=True)
    order_index = models.SmallIntegerField(default=0)
    # TODO: Skill update - remove wikipedia_tags and organization_tags
    wikipedia_tags = models.ManyToManyField(
        "misc.WikipediaTag", related_name="project_categories"
    )
    organization_tags = models.ManyToManyField(
        "misc.Tag", related_name="project_categories"
    )
    tags = models.ManyToManyField(
        "skills.Tag",
        related_name="project_categories",
        blank=True,
        db_table="organizations_projectcategory_skills_tags",  # avoid conflicts with old Tag model
    )
    template = models.OneToOneField(
        Template,
        on_delete=models.PROTECT,
        related_name="project_category",
        null=True,
        default=None,
    )
    only_reviewer_can_publish = models.BooleanField(default=False)
    is_root = models.BooleanField(default=False)
    parent = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, related_name="children"
    )
    history = HistoricalRecords()

    class Meta:
        ordering = ["organization__code", "order_index"]

    def get_related_organizations(self) -> List["Organization"]:
        """Return the organizations related to this model."""
        return [self.organization]

    @classmethod
    def update_or_create_root(cls, organization: "Organization"):
        root_group, _ = cls.objects.update_or_create(
            organization=organization,
            is_root=True,
            defaults={
                "name": organization.name,
            },
        )
        return root_group

    @classmethod
    def _get_hierarchy(cls, categories: dict[int, dict], category_id: int):
        from apps.files.serializers import ImageSerializer

        return {
            "id": categories[category_id].id,
            "name": categories[category_id].name,
            "background_color": categories[category_id].background_color,
            "foreground_color": categories[category_id].foreground_color,
            "background_image": (
                ImageSerializer(categories[category_id].background_image).data
                if categories[category_id].background_image
                else None
            ),
            "children": [
                cls._get_hierarchy(categories, child)
                for child in categories[category_id].children_ids
                if child is not None
            ],
        }

    def get_hierarchy(self):
        # This would be better with a recursive serializer, but it doubles the query time
        categories = ProjectCategory.objects.filter(
            organization=self.organization.pk
        ).annotate(children_ids=ArrayAgg("children"))
        categories = {category.id: category for category in categories}
        return self._get_hierarchy(categories, self.id)
