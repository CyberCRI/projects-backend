from typing import TYPE_CHECKING, Any, List, Optional

from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.aggregates import ArrayAgg
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import Q, QuerySet, UniqueConstraint
from services.translator.mixins import HasAutoTranslatedFields
from simple_history.models import HistoricalRecords

from apps.commons.enums import Language
from apps.commons.mixins import (
    HasMultipleIDs,
    HasPermissionsSetup,
    OrganizationRelated,
)
from apps.commons.models import GroupData
from apps.commons.utils import (
    get_permissions_from_subscopes,
    get_write_permissions_from_subscopes,
)

if TYPE_CHECKING:
    from apps.accounts.models import ProjectUser


class Organization(
    HasAutoTranslatedFields,
    HasPermissionsSetup,
    OrganizationRelated,
    models.Model,
):
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

    organization_query_string: str = ""
    auto_translated_fields: List[str] = [
        "name",
        "dashboard_title",
        "dashboard_subtitle",
        "description",
        "chat_button_text",
    ]

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

    auto_translate_content = models.BooleanField(default=False)
    languages = ArrayField(
        models.CharField(max_length=2, choices=Language.choices),
        default=Language.default_list,
    )
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

    identity_providers = models.ManyToManyField(
        "keycloak.IdentityProvider", related_name="organizations", blank=True
    )
    featured_projects = models.ManyToManyField(
        "projects.Project", related_name="org_featured_projects", blank=True
    )
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
    permissions_up_to_date = models.BooleanField(default=False)

    class Meta:
        subscopes = (
            ("project", "projects"),
            ("projectmessage", "project messages"),
            ("projectuser", "users"),
            ("peoplegroup", "groups"),
            ("news", "news"),
            ("event", "event"),
            ("instruction", "instructions"),
            ("organizationattachmentfile", "organization files"),
        )
        write_only_subscopes = (
            ("tag", "tags"),
            ("tagclassification", "tag classifications"),
            ("projectcategory", "project categories"),
            ("template", "templates"),
            ("review", "reviews"),
            ("comment", "comments"),
            ("follow", "follows"),
            ("invitation", "invitation links"),
        )
        permissions = (
            ("access_admin", "Can access the admin panel"),
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

    def get_default_admins_permissions(self) -> QuerySet[Permission]:
        return Permission.objects.filter(content_type=self.content_type)

    def get_global_admins_permissions(self) -> QuerySet[Permission]:
        return Permission.objects.filter(
            codename__in=[
                "get_user_by_email",
                # TODO: remove that when we have a better way to handle permissions
                "add_projectuser",
                "change_projectuser",
                "delete_projectuser",
            ],
            content_type__app_label="accounts",
        )

    def get_default_facilitators_permissions(self) -> QuerySet[Permission]:
        excluded_permissions = [
            "manage_accessrequest",
            "access_admin",
            *[
                f"{action}_{subscope}"
                for action in ["change", "delete", "add"]
                for subscope in [
                    "tag",
                    "review",
                    "projectcategory",
                    "template",
                    "tagclassification",
                    "organization",
                ]
            ],
        ]
        return Permission.objects.filter(content_type=self.content_type).exclude(
            codename__in=excluded_permissions
        )

    def get_default_users_permissions(self) -> QuerySet[Permission]:
        filtered_permissions = [
            "view_org_project",
            "view_org_projectuser",
            "view_org_peoplegroup",
            "add_project",
            "duplicate_project",
        ]
        return Permission.objects.filter(
            content_type=self.content_type,
            codename__in=filtered_permissions,
        )

    def setup_permissions(
        self, user: Optional["ProjectUser"] = None, trigger_indexation: bool = True
    ):
        """Setup the group with default permissions."""
        admins = self.setup_group_object_permissions(
            self.get_admins(), self.get_default_admins_permissions()
        )
        admins = self.setup_group_global_permissions(
            admins, self.get_global_admins_permissions()
        )
        facilitators = self.setup_group_object_permissions(
            self.get_facilitators(), self.get_default_facilitators_permissions()
        )
        users = self.setup_group_object_permissions(
            self.get_users(), self.get_default_users_permissions()
        )

        if user:
            admins.users.add(user)
        self.groups.set([admins, facilitators, users])
        if trigger_indexation:
            self.permissions_up_to_date = True
            self.save(update_fields=["permissions_up_to_date"])
        else:
            Organization.objects.filter(pk=self.pk).update(permissions_up_to_date=True)

    def get_admins(self) -> Group:
        """Return the admins group."""
        return self.get_or_create_group(GroupData.Role.ADMINS)

    def get_facilitators(self) -> Group:
        """Return the facilitators group."""
        return self.get_or_create_group(GroupData.Role.FACILITATORS)

    def get_users(self) -> Group:
        """Return the users group."""
        return self.get_or_create_group(GroupData.Role.USERS)

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


class TemplateCategories(models.Model):
    """
    Through model for the ManyToMany relationship between templates and categories.

    Attributes
    ----------
    template: ForeignKey
        Template used by the category.
    category: ForeignKey
        Category used by the template.
    always_use: BooleanField
        Whether the template should always be used in the category or not.
    """

    template = models.ForeignKey("organizations.Template", on_delete=models.CASCADE)
    category = models.ForeignKey(
        "organizations.ProjectCategory", on_delete=models.CASCADE
    )
    always_use = models.BooleanField(default=False)


class Template(HasAutoTranslatedFields, OrganizationRelated, models.Model):
    """
    Templates are used to guide the creation a new project by providing placeholders.

    Attributes
    ----------
    name: CharField
        Name of the template.
    description: TextField
        Description of the template.
    language: CharField
        Language of the template.
    images: ManyToManyField
        Images used by the template.
    organization: ForeignKey
        Organization the template is a part of.
    categories: ManyToManyField
        Categories the template can be used in.
    project_title: CharField
        Project created from this template title placeholder.
    project_description: TextField
        Project created from this template description placeholder.
    project_tags: ManyToManyField
        Project created from this template tags placeholder.
    blogentry_title: TextField
        Project's blog entry title placeholder.
    blogentry_content: TextField
        Project's blog entry content placeholder.
    goal_title: CharField
        Project's goal title placeholder.
    goal_description: TextField
        Project's goal description placeholder.
    review_title: CharField
        Project's review title placeholder.
    review_description: TextField
        Project's review description placeholder.
    comment_content: TextField
        Project's comment content placeholder.
    audience: CharField
        Audience this template is intended for.
    time_estimation: CharField
        Time estimation for the project created from this template.
    share_globally: BooleanField
        Whether to share the template globally or keep it in the organization.
    """

    class Audiences(models.TextChoices):
        PRIMARY = "primary"
        MIDDLE = "middle"
        HIGH = "high"
        BACHELOR = "bachelor"
        MASTER = "master"
        PHD = "phd"
        WORK = "work"

    class TimeEstimation(models.TextChoices):
        H1_H10 = "1-10hrs"
        H11_H40 = "11-40hrs"
        H41_H120 = "41-120hrs"
        H121_PLUS = "Over 120hrs"

    auto_translated_fields: List[str] = [
        "name",
        "description",
        "project_title",
        "project_description",
        "blogentry_title",
        "blogentry_content",
        "goal_title",
        "goal_description",
        "review_title",
        "review_description",
        "comment_content",
    ]

    name = models.CharField(max_length=255, blank=True)
    description = models.TextField(default="", blank=True)
    language = models.CharField(
        max_length=2, choices=Language.choices, default=Language.default()
    )
    images = models.ManyToManyField("files.Image", related_name="templates")
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="templates",
        null=True,
    )
    categories = models.ManyToManyField(
        "organizations.ProjectCategory",
        through="organizations.TemplateCategories",
        related_name="templates",
        blank=True,
    )

    project_title = models.CharField(max_length=255, default="", blank=True)
    project_description = models.TextField(default="", blank=True)
    project_tags = models.ManyToManyField(
        "skills.Tag", related_name="templates", blank=True
    )
    blogentry_title = models.TextField(max_length=255, default="", blank=True)
    blogentry_content = models.TextField(default="", blank=True)
    goal_title = models.CharField(max_length=255, default="", blank=True)
    goal_description = models.TextField(blank=True)
    review_title = models.CharField(max_length=255, default="", blank=True)
    review_description = models.TextField(blank=True)
    comment_content = models.TextField(blank=True)

    audience = models.CharField(max_length=20, choices=Audiences.choices, blank=True)
    time_estimation = models.CharField(
        max_length=20, choices=TimeEstimation.choices, blank=True
    )
    share_globally = models.BooleanField(default=False)

    def get_related_organizations(self) -> Organization:
        """Return the organizations related to this model."""
        return [self.organization]


class ProjectCategory(
    HasAutoTranslatedFields, HasMultipleIDs, OrganizationRelated, models.Model
):
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

    auto_translated_fields: List[str] = ["name", "description"]
    slugified_fields: List[str] = ["name"]
    slug_prefix: str = "category"

    name = models.CharField(max_length=100, help_text="name of the category")
    slug = models.SlugField(unique=True)
    outdated_slugs = ArrayField(models.SlugField(), default=list)
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
    tags = models.ManyToManyField(
        "skills.Tag",
        related_name="project_categories",
        blank=True,
        db_table="organizations_projectcategory_skills_tags",  # avoid conflicts with old Tag model
    )
    template = (
        models.OneToOneField(  # TODO: remove this field when templates v2 is ready
            Template,
            on_delete=models.PROTECT,
            related_name="project_category",
            null=True,
            default=None,
        )
    )
    only_reviewer_can_publish = models.BooleanField(default=False)
    is_root = models.BooleanField(default=False)
    parent = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, related_name="children"
    )
    history = HistoricalRecords()

    class Meta:
        ordering = ["organization__code", "order_index"]

    def __str__(self) -> str:
        return self.name

    @classmethod
    def get_id_field_name(cls, object_id: Any) -> str:
        """Get the name of the field which contains the given ID."""
        try:
            int(object_id)
            return "id"
        except ValueError:
            return "slug"

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
            "slug": categories[category_id].slug,
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


class TermsAndConditions(HasAutoTranslatedFields, OrganizationRelated, models.Model):
    """
    Model to store the terms and conditions for an organization.
    """

    auto_translated_fields: List[str] = ["content"]

    organization = models.OneToOneField(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="terms_and_conditions",
    )
    version = models.IntegerField(default=1)
    content = models.TextField(blank=True, default="")
    is_default = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    def get_related_organizations(self) -> List["Organization"]:
        return [self.organization]

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=("is_default",),
                condition=Q(is_default=True),
                name="unique_default_terms_and_conditions",
            )
        ]
