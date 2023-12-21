import uuid
from datetime import date
from typing import TYPE_CHECKING, Any, Iterable, List, Optional

from django.apps import apps
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.aggregates import ArrayAgg
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MaxValueValidator
from django.db import models, transaction
from django.db.models import Q, QuerySet, UniqueConstraint
from django.db.models.manager import Manager
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from guardian.shortcuts import assign_perm, get_objects_for_user

from apps.accounts.utils import (
    default_onboarding_status,
    get_group_permissions,
    get_superadmins_group,
)
from apps.commons.db.abc import (
    HasMultipleIDs,
    HasOwner,
    OrganizationRelated,
    PermissionsSetupModel,
)
from apps.misc.models import SDG, Language, WikipediaTag
from apps.projects.models import Project

if TYPE_CHECKING:
    from apps.organizations.models import Organization


class PeopleGroup(HasMultipleIDs, PermissionsSetupModel, OrganizationRelated):
    """
    A group of users.
    This model is used to group people together, for example to display them on a page.

    Attributes:
    ----------
        people_id: CharField
            The id of the group in the People database.
        name: CharField
            The name of the group.
        description: TextField
            The description of the group.
        short_description: TextField
            Short description of the group in one line.
        email: EmailField
            The contact email of the group.
        type: CharField
            The type of the group.
        sdgs: ArrayField
            UN Sustainable Development Goals this group try to achieve.
        parent: ForeignKey
            The parent group of this group.
        organization: ForeignKey
            The organization this group belongs to.
        header_image: ForeignKey
            The header image of the group.
        logo: ForeignKey
            The logo of the group.
        featured_projects: ManyToManyField
            The projects this group wants to put forward.
        groups: ManyToManyField
            The permission groups related to this group.
        publication_status: CharField
            The visibility setting of the group.
    """

    class PublicationStatus(models.TextChoices):
        """Visibility setting of a people group."""

        PUBLIC = "public"
        PRIVATE = "private"
        ORG = "org"

    class DefaultGroup(models.TextChoices):
        """Default permission groups of a people group."""

        MEMBERS = "members"
        MANAGERS = "managers"
        LEADERS = "leaders"

    name = models.CharField(max_length=255, blank=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    short_description = models.TextField(blank=True)
    email = models.EmailField(blank=True)
    type = models.CharField(max_length=50, blank=True)
    sdgs = ArrayField(
        models.PositiveSmallIntegerField(choices=SDG.choices, unique=True),
        len(SDG),
        default=list,
        null=True,
    )
    parent = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, related_name="children"
    )
    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, null=True
    )
    header_image = models.ForeignKey(
        "files.Image",
        on_delete=models.SET_NULL,
        null=True,
        related_name="people_group_header",
    )
    logo_image = models.ForeignKey(
        "files.Image",
        on_delete=models.SET_NULL,
        null=True,
        related_name="people_group_logo",
    )
    featured_projects = models.ManyToManyField(
        "projects.Project", related_name="people_groups"
    )
    groups = models.ManyToManyField(Group, related_name="people_groups")
    publication_status = models.CharField(
        max_length=10,
        choices=PublicationStatus.choices,
        default=PublicationStatus.ORG,
        verbose_name=_("visibility"),
    )
    is_root = models.BooleanField(default=False)

    # TODO : Delete these fields when people migration is done
    people_data = models.JSONField(default=dict)
    people_id = models.CharField(max_length=255)
    order = models.IntegerField(null=True)

    def __str__(self) -> str:
        return str(self.name)

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
        return [self.organization] if self.organization else []

    @property
    def content_type(self) -> ContentType:
        """Return the content type of the model."""
        return ContentType.objects.get_for_model(PeopleGroup)

    @classmethod
    def _get_hierarchy(cls, groups: dict[int, dict], group_id: int):
        from apps.files.serializers import ImageSerializer

        return {
            "id": groups[group_id].id,
            "slug": groups[group_id].slug,
            "name": groups[group_id].name,
            "type": groups[group_id].type,
            "publication_status": groups[group_id].publication_status,
            "children": [
                cls._get_hierarchy(groups, child)
                for child in groups[group_id].children_ids
                if child is not None and groups[child].type == "group"
            ],
            "roles": [group.name for group in groups[group_id].groups.all()],
            "header_image": ImageSerializer(groups[group_id].header_image).data
            if groups[group_id].header_image
            else None,
        }

    def get_hierarchy(self):
        # This would be better with a recursive serializer, but it doubles the query time
        groups = PeopleGroup.objects.filter(organization=self.organization.pk).annotate(
            children_ids=ArrayAgg("children")
        )
        groups = {group.id: group for group in groups}
        return self._get_hierarchy(groups, self.id)

    def get_default_managers_permissions(self) -> Iterable[Permission]:
        return Permission.objects.filter(content_type=self.content_type)

    def get_default_members_permissions(self) -> Iterable[Permission]:
        return Permission.objects.filter(
            content_type=self.content_type, codename="view_peoplegroup"
        )

    def get_default_leaders_permissions(self) -> Iterable[Permission]:
        return Permission.objects.filter(content_type=self.content_type)

    def setup_permissions(self, user: Optional["ProjectUser"] = None):
        """Setup the group with default permissions."""
        managers = self.get_managers()
        managers.permissions.clear()
        for permission in self.get_default_managers_permissions():
            assign_perm(permission, managers, self)

        members = self.get_members()
        members.permissions.clear()
        for permission in self.get_default_members_permissions():
            assign_perm(permission, members, self)

        leaders = self.get_leaders()
        leaders.permissions.clear()
        for permission in self.get_default_leaders_permissions():
            assign_perm(permission, leaders, self)

        if user:
            managers.users.add(user)
        self.groups.add(managers, members, leaders)
        self.permissions_up_to_date = True
        # Saving is also mandatory to trigger indexing in Algolia
        self.save(update_fields=["permissions_up_to_date"])

    def remove_duplicated_roles(self):
        """Remove duplicated roles in the group."""
        self.members.set(
            self.members.exclude(
                pk__in=self.managers.values_list("pk", flat=True)
            ).exclude(pk__in=self.leaders.values_list("pk", flat=True))
        )
        self.managers.set(
            self.managers.exclude(pk__in=self.leaders.values_list("pk", flat=True))
        )

    def get_or_create_group(self, name: str) -> Group:
        """Return the group with the given name."""
        group, created = Group.objects.get_or_create(
            name=f"{self.content_type.model}:#{self.pk}:{name}"
        )
        if created:
            self.groups.add(group)
        return group

    def get_managers(self) -> Group:
        """Return the managers group."""
        return self.get_or_create_group(self.DefaultGroup.MANAGERS)

    def get_members(self) -> Group:
        """Return the members group."""
        return self.get_or_create_group(self.DefaultGroup.MEMBERS)

    def get_leaders(self) -> Group:
        """Return the leaders group."""
        return self.get_or_create_group(self.DefaultGroup.LEADERS)

    @property
    def managers(self) -> List["ProjectUser"]:
        return self.get_managers().users

    @property
    def members(self) -> List["ProjectUser"]:
        return self.get_members().users

    @property
    def leaders(self) -> List["ProjectUser"]:
        return self.get_leaders().users

    def get_all_members(self) -> List["ProjectUser"]:
        """Return the all members."""
        return (
            self.managers.all() | self.members.all() | self.leaders.all()
        ).distinct()

    def get_slug(self) -> str:
        if self.slug == "":
            name = self.name
            if name == "":
                name = self.type or "group"
            raw_slug = slugify(name[0:46])
            try:
                int(raw_slug)
                raw_slug = f"group-{raw_slug}"  # Prevent clashes with IDs
            except ValueError:
                pass
            slug = raw_slug
            same_slug_count = 0
            while PeopleGroup.objects.filter(slug=slug).exists():
                same_slug_count += 1
                slug = f"{raw_slug}-{same_slug_count}"
            return slug
        return self.slug

    @transaction.atomic
    def save(self, *args, **kwargs):
        self.slug = self.get_slug()
        super().save(*args, **kwargs)

    class Meta:
        constraints = [
            UniqueConstraint(
                name="unique_root_group_per_organization",
                fields=["organization"],
                condition=Q(is_root=True),
            ),
        ]


class ProjectUser(AbstractUser, HasMultipleIDs, HasOwner, OrganizationRelated):
    """
    Override Django base user by a user of projects app
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._project_queryset: Optional[QuerySet["Project"]] = None
        self._user_queryset: Optional[QuerySet["ProjectUser"]] = None
        self._people_group_queryset: Optional[QuerySet["PeopleGroup"]] = None

    # AbstractUser unused fields
    username_validator = None
    username = None
    first_name = None
    last_name = None
    date_joined = None
    password = None
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    people_id = models.UUIDField(
        auto_created=False, unique=True, null=True, help_text="id of user in people"
    )
    external_id = models.CharField(
        max_length=255,
        blank=True,
        help_text="id of user in their organization",
    )
    email = models.CharField(max_length=255, unique=True)
    given_name = models.CharField(max_length=255, blank=True)
    family_name = models.CharField(max_length=255, blank=True)
    slug = models.SlugField(unique=True)
    groups = models.ManyToManyField(Group, related_name="users")
    language = models.CharField(
        max_length=2, choices=Language.choices, default=Language.default()
    )
    created_at = models.DateTimeField(auto_now_add=True)
    onboarding_status = models.JSONField(default=default_onboarding_status)

    # Profile fields
    birthdate = models.DateField(
        max_length=255,
        null=True,
        blank=True,
        validators=[MaxValueValidator(limit_value=date.today)],
    )
    pronouns = models.CharField(max_length=32, blank=True)
    personal_description = models.TextField(blank=True)
    short_description = models.TextField(blank=True)
    professional_description = models.TextField(blank=True)
    location = models.TextField(blank=True)
    job = models.CharField(max_length=255, blank=True)
    profile_picture = models.ForeignKey(
        "files.Image", on_delete=models.SET_NULL, null=True, related_name="user"
    )
    sdgs = ArrayField(
        models.PositiveSmallIntegerField(choices=SDG.choices, unique=True),
        len(SDG),
        default=list,
        null=True,
    )

    # Social fields
    facebook = models.URLField(blank=True)
    mobile_phone = models.CharField(blank=True, max_length=255)
    linkedin = models.URLField(blank=True)
    medium = models.URLField(blank=True)
    website = models.CharField(blank=True, max_length=255)
    personal_email = models.EmailField(blank=True)
    skype = models.CharField(blank=True, max_length=255)
    landline_phone = models.CharField(blank=True, max_length=255)
    twitter = models.URLField(blank=True)

    # TODO : Delete these fields when people migration is done
    people_data = models.JSONField(default=dict)
    type = models.CharField(max_length=255, blank=True, default="")

    def __str__(self):
        return self.get_full_name()

    @property
    def keycloak_id(self):
        if hasattr(self, "keycloak_account"):
            return str(self.keycloak_account.keycloak_id)
        return None

    @property
    def is_superuser(self):
        """
        Return True if user is in the superadmins group
        """
        return self in get_superadmins_group().users.all()

    @property
    def is_staff(self):
        """
        Needs to return True if user can access admin site
        """
        return self.is_superuser

    @classmethod
    def get_id_field_name(cls, object_id: Any) -> str:
        """Get the name of the field which contains the given ID."""
        try:
            uuid.UUID(object_id)
            return "keycloak_account__keycloak_id"
        except (ValueError, AttributeError):
            try:
                int(object_id)
                return "id"
            except ValueError:
                return "slug"

    def is_owned_by(self, user: "ProjectUser") -> bool:
        """Whether the given user is the owner of the object."""
        return self == user

    def get_owner(self):
        """Get the owner of the object."""
        return self

    def get_related_organizations(self) -> List["Organization"]:
        """Return the organizations related to this model."""
        Organization = apps.get_model("organizations", "Organization")  # noqa
        return list(Organization.objects.filter(groups__users=self).distinct())

    def get_full_name(self):
        """Return the first_name plus the last_name, with a space in between."""
        return f"{self.given_name.capitalize()} {self.family_name.capitalize()}".strip()

    def get_project_queryset(self, *prefetch) -> QuerySet["Project"]:
        if self._project_queryset is None:
            if self.is_superuser:
                self._project_queryset = Project.objects.all().distinct()
            else:
                public_projects = Project.objects.filter(
                    publication_status=Project.PublicationStatus.PUBLIC
                )
                member_projects = get_objects_for_user(self, "projects.view_project")
                org_user_projects = Project.objects.filter(
                    publication_status=Project.PublicationStatus.ORG,
                    organizations__in=get_objects_for_user(
                        self, "organizations.view_org_project"
                    ),
                )
                org_admin_projects = Project.objects.filter(
                    organizations__in=get_objects_for_user(
                        self, "organizations.view_project"
                    )
                )
                qs = (
                    public_projects.union(member_projects)
                    .union(org_user_projects)
                    .union(org_admin_projects)
                )
                self._project_queryset = Project.objects.filter(
                    id__in=qs.values("id")
                ).distinct()
        return self._project_queryset.prefetch_related(*prefetch)

    def get_user_queryset(self, *prefetch) -> QuerySet["ProjectUser"]:
        if self._user_queryset is None:
            if self.is_superuser:
                self._user_queryset = ProjectUser.objects.all().distinct()
            else:
                request_user = ProjectUser.objects.filter(id=self.id)
                public_users = ProjectUser.objects.filter(
                    privacy_settings__publication_status=PrivacySettings.PrivacyChoices.PUBLIC
                )
                org_user_users = ProjectUser.objects.filter(
                    privacy_settings__publication_status=PrivacySettings.PrivacyChoices.ORGANIZATION,
                    groups__organizations__in=get_objects_for_user(
                        self, "organizations.view_org_projectuser"
                    ),
                )
                org_admin_users = ProjectUser.objects.filter(
                    groups__organizations__in=get_objects_for_user(
                        self, "organizations.view_projectuser"
                    )
                )

                qs = (
                    request_user.union(public_users)
                    .union(org_user_users)
                    .union(org_admin_users)
                )
                self._user_queryset = ProjectUser.objects.filter(
                    id__in=qs.values("id")
                ).distinct()
        return self._user_queryset.prefetch_related(*prefetch)

    def get_people_group_queryset(self, *prefetch) -> QuerySet["PeopleGroup"]:
        if self._people_group_queryset is None:
            if self.is_superuser:
                self._people_group_queryset = PeopleGroup.objects.all().distinct()
            else:
                public_groups = PeopleGroup.objects.filter(
                    publication_status=PeopleGroup.PublicationStatus.PUBLIC
                )
                member_groups = get_objects_for_user(self, "accounts.view_peoplegroup")
                org_user_groups = PeopleGroup.objects.filter(
                    publication_status=PeopleGroup.PublicationStatus.ORG,
                    organization__in=get_objects_for_user(
                        self, "organizations.view_org_peoplegroup"
                    ),
                )
                org_admin_groups = PeopleGroup.objects.filter(
                    organization__in=get_objects_for_user(
                        self, "organizations.view_peoplegroup"
                    )
                )
                qs = (
                    public_groups.union(member_groups)
                    .union(org_user_groups)
                    .union(org_admin_groups)
                )
                self._people_group_queryset = PeopleGroup.objects.filter(
                    id__in=qs.values("id")
                ).distinct()
        return self._people_group_queryset.prefetch_related(*prefetch)

    def get_project_related_queryset(
        self, queryset: QuerySet, project_related_name: str = "project"
    ):
        return queryset.filter(
            **{f"{project_related_name}__in": self.get_project_queryset()}
        )

    def get_user_related_queryset(
        self, queryset: QuerySet, user_related_name: str = "user"
    ):
        return queryset.filter(**{f"{user_related_name}__in": self.get_user_queryset()})

    def can_see_project(self, project):
        """Return a `BasePermission` according to `linked_project`'s publication status."""
        return project in self.get_project_queryset()

    def get_permissions_representations(self):
        """Return a list of the permissions representations."""
        groups_permissions = [
            get_group_permissions(group) for group in self.groups.all()
        ]
        groups_permissions = [
            permission
            for group_permissions in groups_permissions
            for permission in group_permissions
        ]
        return list(set(groups_permissions))

    def get_instance_permissions_representations(self):
        """Return a list of the instance permissions representations."""
        groups = self.groups.exclude(
            projects=None, people_groups=None, organizations=None
        )
        groups_permissions = [get_group_permissions(group) for group in groups]
        groups_permissions = [
            permission
            for group_permissions in groups_permissions
            for permission in group_permissions
        ]
        return list(set(groups_permissions))

    def get_slug(self) -> str:
        """
        Generates a unique slug for the user based on their first and last names.
        If the generated slug already exists, a numerical suffix is appended for uniqueness.
        If the slug is purely numerical, "-1" is appended to prevent clashes with IDs.
        If the slug is an uuid, "-1" is appended to prevent clashes with keycloak_ids.
        """
        if self.slug == "":
            full_name = self.get_full_name()
            if full_name == "":
                full_name = self.email.split("@")[0] or "user"
            raw_slug = slugify(full_name[0:46])
            try:
                int(raw_slug)
                raw_slug = f"user-{raw_slug}"  # Prevent clashes with IDs
            except ValueError:
                pass
            try:
                uuid.UUID(raw_slug)
                raw_slug = f"user-{raw_slug}"  # Prevent clashes with keycloak_ids
            except ValueError:
                pass
            slug = raw_slug
            same_slug_count = 0
            while ProjectUser.objects.filter(slug=slug).exists():
                same_slug_count += 1
                slug = f"{raw_slug}-{same_slug_count}"
            try:
                int(slug)
                slug = f"{slug}-1"
            except ValueError:
                pass
            try:
                uuid.UUID(slug)
                slug = f"{slug}-1"
            except ValueError:
                pass
            return slug
        return self.slug

    @transaction.atomic
    def save(self, *args, **kwargs):
        self.slug = self.get_slug()
        super().save(*args, **kwargs)


class PrivacySettings(models.Model, HasOwner):
    class PrivacyChoices(models.TextChoices):
        HIDE = "hide", _("Hide")
        ORGANIZATION = "org", _("Organization")
        PUBLIC = "pub", _("Public")

    PRIVACY_CHARFIELD = {
        "max_length": 4,
        "choices": PrivacyChoices.choices,
    }

    user = models.OneToOneField(
        ProjectUser,
        on_delete=models.CASCADE,
        related_name="privacy_settings",
    )
    publication_status = models.CharField(
        **PRIVACY_CHARFIELD,
        default=PrivacyChoices.PUBLIC,
    )
    profile_picture = models.CharField(
        **PRIVACY_CHARFIELD,
        default=PrivacyChoices.ORGANIZATION,
    )
    skills = models.CharField(
        **PRIVACY_CHARFIELD,
        default=PrivacyChoices.PUBLIC,
    )
    mobile_phone = models.CharField(
        **PRIVACY_CHARFIELD,
        default=PrivacyChoices.ORGANIZATION,
    )
    personal_email = models.CharField(
        **PRIVACY_CHARFIELD,
        default=PrivacyChoices.ORGANIZATION,
    )
    socials = models.CharField(
        **PRIVACY_CHARFIELD,
        default=PrivacyChoices.ORGANIZATION,
    )

    def is_owned_by(self, user: "ProjectUser") -> bool:
        """Whether the given user is the owner of the object."""
        return self.user == user

    def get_owner(self):
        """Get the owner of the object."""
        return self.user


class Skill(models.Model, HasOwner):
    class SkillType(models.TextChoices):
        """Visibility setting of a project."""

        SKILL = "skill"
        HOBBY = "hobby"

    user = models.ForeignKey(
        ProjectUser, on_delete=models.CASCADE, related_name="skills"
    )
    type = models.CharField(
        max_length=8, choices=SkillType.choices, default=SkillType.SKILL.value
    )
    wikipedia_tag = models.ForeignKey(WikipediaTag, on_delete=models.CASCADE)
    level = models.SmallIntegerField()
    level_to_reach = models.SmallIntegerField()
    category = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "wikipedia_tag"], name="unique user wikipedia_tag"
            )
        ]

    def is_owned_by(self, user: "ProjectUser") -> bool:
        """Whether the given user is the owner of the object."""
        return self.user == user

    def get_owner(self):
        """Get the owner of the object."""
        return self.user


class AnonymousUser:
    """An anonymous user with most of the same feature as `ProjectUser`."""

    id = None
    pk = None
    keycloak_id = None
    people_id = None
    given_name = "Anonymous"
    family_name = "User"
    email = ""
    username = ""
    is_superuser = False
    is_authenticated = False
    is_anonymous = True
    _groups = Group.objects.none()
    _user_queryset = None
    _project_queryset = None
    _people_group_queryset = None

    def __str__(self) -> str:
        return "AnonymousUser"

    def __eq__(self, other) -> bool:
        return isinstance(other, self.__class__)

    def __hash__(self) -> int:
        return 1

    @property
    def groups(self) -> Manager:
        return self._groups

    def get_full_name(self):
        """Return the first_name plus the last_name, with a space in between."""
        return f"{self.given_name} {self.family_name}".strip()

    @classmethod
    def serialize(cls, with_permissions=True):
        data = {
            "id": cls.id,
            "keycloak_id": cls.keycloak_id,
            "people_id": cls.people_id,
            "email": cls.email,
            "given_name": cls.given_name,
            "family_name": cls.family_name,
            "pronouns": "",
            "job": "Anonymous user",
            "profile_picture": None,
        }
        if with_permissions:
            return {
                **data,
                "groups": [g.representation for g in cls.groups.all()],
            }
        return data

    def get_project_queryset(self, *prefetch) -> QuerySet["Project"]:
        if self._project_queryset is None:
            self._project_queryset = Project.objects.filter(
                publication_status=Project.PublicationStatus.PUBLIC
            ).distinct()
        return self._project_queryset.prefetch_related(*prefetch)

    def get_user_queryset(self, *prefetch) -> QuerySet["ProjectUser"]:
        if self._user_queryset is None:
            self._user_queryset = ProjectUser.objects.filter(
                privacy_settings__publication_status=PrivacySettings.PrivacyChoices.PUBLIC
            )
        return self._user_queryset.prefetch_related(*prefetch)

    def get_people_group_queryset(self, *prefetch) -> QuerySet["PeopleGroup"]:
        if self._people_group_queryset is None:
            self._people_group_queryset = PeopleGroup.objects.filter(
                publication_status=PeopleGroup.PublicationStatus.PUBLIC
            )
        return self._people_group_queryset.prefetch_related(*prefetch)

    def get_project_related_queryset(
        self, queryset: QuerySet, project_related_name: str = "project"
    ):
        return queryset.filter(
            **{
                f"{project_related_name}__publication_status": Project.PublicationStatus.PUBLIC
            }
        )

    def get_user_related_queryset(
        self, queryset: QuerySet, user_related_name: str = "user"
    ):
        return queryset.filter(
            **{
                f"{user_related_name}__privacy_settings__publication_status": PrivacySettings.PrivacyChoices.PUBLIC
            }
        )

    def can_see_project(self, project):
        return project.publication_status == Project.PublicationStatus.PUBLIC

    def get_permissions_representations(self):
        """Return a list of the permissions representations."""
        return []

    def get_related_organizations(self) -> List["Organization"]:
        """Return the organizations related to this model."""
        return []


class InvitationUser(AnonymousUser):
    def __init__(self, invitation):
        self.invitation = invitation

    is_authenticated = True
    _permissions = Permission.objects.filter(codename__in=["add_projectuser"])

    def has_perm(self, perm, obj=None):
        return perm == "accounts.add_projectuser"


class AccessRequest(models.Model):
    """ """

    class Status(models.TextChoices):
        PENDING = "pending"
        ACCEPTED = "accepted"
        DECLINED = "declined"

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="access_requests",
    )
    user = models.ForeignKey(
        ProjectUser, on_delete=models.CASCADE, related_name="access_requests", null=True
    )
    email = models.CharField(max_length=255, blank=True)
    given_name = models.CharField(max_length=255, blank=True)
    family_name = models.CharField(max_length=255, blank=True)
    job = models.CharField(max_length=255, blank=True)
    message = models.TextField(blank=True)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.given_name} {self.family_name} ({self.email})"

    def get_related_organizations(self) -> List["Organization"]:
        """Return the organizations related to this model."""
        return [self.organization]

    class Meta:
        permissions = (("manage_accessrequest", "Can manage access requests"),)
