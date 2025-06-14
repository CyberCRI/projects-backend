import math
import uuid
from datetime import date
from typing import Any, List, Optional, Union

from django.contrib.auth.models import AbstractUser, Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.aggregates import ArrayAgg
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MaxValueValidator
from django.db import models, transaction
from django.db.models import Q, QuerySet, UniqueConstraint
from django.db.models.manager import Manager
from django.http import Http404
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from guardian.shortcuts import get_objects_for_user

from apps.accounts.utils import (
    default_onboarding_status,
    get_default_group,
    get_group_permissions,
    get_superadmins_group,
)
from apps.commons.enums import SDG, Language
from apps.commons.mixins import (
    HasMultipleIDs,
    HasOwner,
    HasPermissionsSetup,
    OrganizationRelated,
)
from apps.commons.models import GroupData
from apps.newsfeed.models import Event, Instruction, News
from apps.organizations.models import Organization
from apps.projects.models import Project
from keycloak import KeycloakGetError
from services.keycloak.exceptions import RemoteKeycloakAccountNotFound
from services.keycloak.interface import KeycloakService
from services.keycloak.models import KeycloakAccount


class PeopleGroup(
    HasMultipleIDs, HasPermissionsSetup, OrganizationRelated, models.Model
):
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

    slugified_fields: List[str] = ["name"]
    slug_prefix: str = "group"

    class PublicationStatus(models.TextChoices):
        """Visibility setting of a people group."""

        PUBLIC = "public"
        PRIVATE = "private"
        ORG = "org"

    name = models.CharField(max_length=255, blank=True)
    slug = models.SlugField(unique=True)
    outdated_slugs = ArrayField(models.SlugField(), default=list)
    description = models.TextField(blank=True)
    short_description = models.TextField(blank=True)
    email = models.EmailField(blank=True)
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
        "organizations.Organization",
        on_delete=models.CASCADE,
        null=True,
        related_name="people_groups",
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
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    permissions_up_to_date = models.BooleanField(default=False)

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
    def _get_hierarchy(cls, groups: dict[int, dict], group_id: int):
        from apps.files.serializers import ImageSerializer

        return {
            "id": groups[group_id].id,
            "slug": groups[group_id].slug,
            "name": groups[group_id].name,
            "publication_status": groups[group_id].publication_status,
            "children": [
                cls._get_hierarchy(groups, child)
                for child in groups[group_id].children_ids
                if child is not None and child in groups
            ],
            "roles": [group.name for group in groups[group_id].groups.all()],
            "header_image": (
                ImageSerializer(groups[group_id].header_image).data
                if groups[group_id].header_image
                else None
            ),
        }

    def get_hierarchy(self, user: Optional["ProjectUser"] = None) -> dict:
        # This would be better with a recursive serializer, but it doubles the query time
        if user:
            groups = (
                user.get_people_group_queryset()
                | PeopleGroup.objects.filter(is_root=True).distinct()
            )
        else:
            groups = PeopleGroup.objects.all()
        groups = groups.filter(organization=self.organization.pk).annotate(
            children_ids=ArrayAgg("children")
        )
        groups = {group.id: group for group in groups}
        return self._get_hierarchy(groups, self.id)

    def get_default_managers_permissions(self) -> QuerySet[Permission]:
        return Permission.objects.filter(content_type=self.content_type)

    def get_default_members_permissions(self) -> QuerySet[Permission]:
        return Permission.objects.filter(
            content_type=self.content_type, codename="view_peoplegroup"
        )

    def get_default_leaders_permissions(self) -> QuerySet[Permission]:
        return Permission.objects.filter(content_type=self.content_type)

    def setup_permissions(
        self, user: Optional["ProjectUser"] = None, trigger_indexation: bool = True
    ):
        """Setup the group with default permissions."""
        managers = self.setup_group_object_permissions(
            self.get_managers(), self.get_default_managers_permissions()
        )
        members = self.setup_group_object_permissions(
            self.get_members(), self.get_default_members_permissions()
        )
        leaders = self.setup_group_object_permissions(
            self.get_leaders(), self.get_default_leaders_permissions()
        )
        if user:
            managers.users.add(user)
        self.groups.set([managers, members, leaders])
        if trigger_indexation:
            self.permissions_up_to_date = True
            self.save(update_fields=["permissions_up_to_date"])
        else:
            PeopleGroup.objects.filter(pk=self.pk).update(permissions_up_to_date=True)

    def get_managers(self) -> Group:
        """Return the managers group."""
        return self.get_or_create_group(GroupData.Role.MANAGERS)

    def get_members(self) -> Group:
        """Return the members group."""
        return self.get_or_create_group(GroupData.Role.MEMBERS)

    def get_leaders(self) -> Group:
        """Return the leaders group."""
        return self.get_or_create_group(GroupData.Role.LEADERS)

    @property
    def managers(self) -> QuerySet["ProjectUser"]:
        return self.get_managers().users

    @property
    def members(self) -> QuerySet["ProjectUser"]:
        return self.get_members().users

    @property
    def leaders(self) -> QuerySet["ProjectUser"]:
        return self.get_leaders().users

    def get_all_members(self) -> QuerySet["ProjectUser"]:
        """Return the all members."""
        return (
            self.managers.all() | self.members.all() | self.leaders.all()
        ).distinct()

    def set_role_groups_members(self):
        projects = Project.objects.filter(groups__people_groups=self).distinct()
        if projects.exists():
            for project in projects:
                for group in project.groups.filter(people_groups=self):
                    project.set_role_group_members(group)

    class Meta:
        constraints = [
            UniqueConstraint(
                name="unique_root_group_per_organization",
                fields=["organization"],
                condition=Q(is_root=True),
            ),
        ]


class ProjectUser(HasMultipleIDs, HasOwner, OrganizationRelated, AbstractUser):
    """
    Override Django base user by a user of projects app
    """

    slugified_fields: List[str] = ["given_name", "family_name"]
    slug_prefix: str = "user"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._project_queryset: Optional[QuerySet["Project"]] = None
        self._user_queryset: Optional[QuerySet["ProjectUser"]] = None
        self._people_group_queryset: Optional[QuerySet["PeopleGroup"]] = None
        self._news_queryset: Optional[QuerySet["News"]] = None
        self._event_queryset: Optional[QuerySet["Event"]] = None
        self._instruction_queryset: Optional[QuerySet["Instruction"]] = None

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
    outdated_slugs = ArrayField(models.SlugField(), default=list)
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
    description = models.TextField(blank=True)
    # TODO: remove these two fields in the future
    personal_description = models.TextField(blank=True)
    professional_description = models.TextField(blank=True)

    short_description = models.TextField(blank=True)
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

    def __str__(self):
        return self.get_full_name()

    class Meta:
        permissions = (("get_user_by_email", "Can retrieve a user by email"),)

    @property
    def keycloak_id(self) -> Optional[uuid.UUID]:
        if hasattr(self, "keycloak_account"):
            return str(self.keycloak_account.keycloak_id)
        return None

    @property
    def is_superuser(self) -> bool:
        """
        Return True if user is in the superadmins group
        """
        return self in get_superadmins_group().users.all()

    @property
    def is_staff(self) -> bool:
        """
        Needs to return True if user can access admin site
        """
        return (
            self.is_superuser
            or get_objects_for_user(
                self, "organizations.access_admin", Organization
            ).exists()
        )

    @classmethod
    def get_id_field_name(cls, object_id: Union[uuid.UUID, int, str]) -> str:
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

    @classmethod
    def get_main_id(
        cls, object_id: Union[uuid.UUID, int, str], returned_field: str = "id"
    ) -> Any:
        try:
            return super().get_main_id(object_id, returned_field)
        except Http404 as e:
            try:
                user = cls.import_from_keycloak(object_id)
                return getattr(user, returned_field)
            except RemoteKeycloakAccountNotFound:
                raise e

    @classmethod
    @transaction.atomic
    def import_from_keycloak(cls, keycloak_id: str) -> "ProjectUser":
        try:
            keycloak_user = KeycloakService.get_user(keycloak_id)
        except KeycloakGetError:
            raise RemoteKeycloakAccountNotFound
        user = cls.objects.create(
            email=keycloak_user.get("username", ""),
            given_name=keycloak_user.get("firstName", ""),
            family_name=keycloak_user.get("lastName", ""),
        )
        keycloak_account = KeycloakAccount.objects.create(
            keycloak_id=keycloak_id,
            username=keycloak_user.get("username", ""),
            email=keycloak_user.get("email", ""),
            user=user,
        )
        if KeycloakService.is_superuser(keycloak_account):
            user.groups.add(get_superadmins_group())
        # Users imported from an external IdP can be added to one or more organizations
        organizations_codes = keycloak_user.get("attributes", {}).get(
            "idp_organizations", []
        )
        organizations = Organization.objects.filter(code__in=organizations_codes)
        user.groups.add(
            get_default_group(),
            *[o.get_users() for o in organizations],
        )
        return user

    def add_idp_organizations(self) -> "ProjectUser":
        try:
            keycloak_user = KeycloakService.get_user(self.keycloak_id)
            organizations_codes = keycloak_user.get("attributes", {}).get(
                "idp_organizations", []
            )
            organizations = Organization.objects.filter(
                code__in=organizations_codes
            ).exclude(groups__users=self)
            self.groups.add(*[o.get_users() for o in organizations])
        except KeycloakGetError:  # Needed for tests to pass
            pass
        return self

    def is_owned_by(self, user: "ProjectUser") -> bool:
        """Whether the given user is the owner of the object."""
        return self == user

    def get_owner(self) -> "ProjectUser":
        """Get the owner of the object."""
        return self

    def get_related_organizations(self) -> List["Organization"]:
        """Return the organizations related to this model."""
        return list(Organization.objects.filter(groups__users=self).distinct())

    def get_full_name(self) -> str:
        """Return the first_name plus the last_name, with a space in between."""
        return f"{self.given_name.capitalize()} {self.family_name.capitalize()}".strip()

    def get_project_queryset(self) -> QuerySet["Project"]:
        if self._project_queryset is None:
            if self.is_superuser:
                self._project_queryset = Project.objects.all()
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
                self._project_queryset = Project.objects.filter(id__in=qs.values("id"))
        return self._project_queryset.distinct()

    def get_news_queryset(self) -> QuerySet["News"]:
        if self._news_queryset is None:
            if self.is_superuser:
                self._news_queryset = News.objects.all()
            else:
                groups = PeopleGroup.objects.filter(groups__users=self)
                organizations = self.get_related_organizations()
                self._news_queryset = News.objects.filter(
                    Q(visible_by_all=True)
                    | Q(people_groups__in=groups)
                    | (
                        Q(organization__in=organizations)
                        & Q(people_groups__isnull=True)
                    )
                    | Q(
                        organization__in=get_objects_for_user(
                            self, "organizations.view_news"
                        )
                    )
                )
        return self._news_queryset.distinct()

    def get_instruction_queryset(self) -> QuerySet["Instruction"]:
        if self._instruction_queryset is None:
            if self.is_superuser:
                self._instruction_queryset = Instruction.objects.all()
            else:
                groups = PeopleGroup.objects.filter(groups__users=self)
                organizations = self.get_related_organizations()
                self._instruction_queryset = Instruction.objects.filter(
                    Q(visible_by_all=True)
                    | Q(people_groups__in=groups)
                    | (
                        Q(organization__in=organizations)
                        & Q(people_groups__isnull=True)
                    )
                    | Q(
                        organization__in=get_objects_for_user(
                            self, "organizations.view_instruction"
                        )
                    )
                )
        return self._instruction_queryset.distinct()

    def get_event_queryset(self) -> QuerySet["Event"]:
        if self._event_queryset is None:
            if self.is_superuser:
                self._event_queryset = Event.objects.all()
            else:
                groups = PeopleGroup.objects.filter(groups__users=self)
                organizations = self.get_related_organizations()
                self._event_queryset = Event.objects.filter(
                    Q(visible_by_all=True)
                    | Q(people_groups__in=groups)
                    | (
                        Q(organization__in=organizations)
                        & Q(people_groups__isnull=True)
                    )
                    | Q(
                        organization__in=get_objects_for_user(
                            self, "organizations.view_event"
                        )
                    )
                )
        return self._event_queryset.distinct()

    def get_user_queryset(self) -> QuerySet["ProjectUser"]:
        if self._user_queryset is None:
            if self.is_superuser:
                self._user_queryset = ProjectUser.objects.all()
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
                self._user_queryset = ProjectUser.objects.filter(id__in=qs.values("id"))
        return self._user_queryset.distinct()

    def get_people_group_queryset(self) -> QuerySet["PeopleGroup"]:
        if self._people_group_queryset is None:
            if self.is_superuser:
                self._people_group_queryset = PeopleGroup.objects.all()
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
                )
        return self._people_group_queryset.distinct()

    def get_project_related_queryset(
        self, queryset: QuerySet, project_related_name: str = "project"
    ) -> QuerySet["Project"]:
        return queryset.filter(
            **{f"{project_related_name}__in": self.get_project_queryset()}
        )

    def get_user_related_queryset(
        self, queryset: QuerySet, user_related_name: str = "user"
    ) -> QuerySet["ProjectUser"]:
        return queryset.filter(**{f"{user_related_name}__in": self.get_user_queryset()})

    def get_people_group_related_queryset(
        self, queryset: QuerySet, people_group_related_name: str = "people_group"
    ) -> QuerySet["PeopleGroup"]:
        return queryset.filter(
            **{f"{people_group_related_name}__in": self.get_people_group_queryset()}
        )

    def get_news_related_queryset(
        self, queryset: QuerySet, news_related_name: str = "news"
    ) -> QuerySet["News"]:
        return queryset.filter(**{f"{news_related_name}__in": self.get_news_queryset()})

    def get_instruction_related_queryset(
        self, queryset: QuerySet, instruction_related_name: str = "instruction"
    ) -> QuerySet["Instruction"]:
        return queryset.filter(
            **{f"{instruction_related_name}__in": self.get_instruction_queryset()}
        )

    def get_event_related_queryset(
        self, queryset: QuerySet, event_related_name: str = "event"
    ) -> QuerySet["Event"]:
        return queryset.filter(
            **{f"{event_related_name}__in": self.get_event_queryset()}
        )

    def can_see_project(self, project: "Project") -> bool:
        """Whether the user can see the project."""
        return project in self.get_project_queryset()

    def get_permissions_representations(self) -> List[str]:
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

    def get_instance_permissions_representations(self) -> List[str]:
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

    def get_or_create_score(self) -> "UserScore":
        score, created = UserScore.objects.get_or_create(user=self)
        if created:
            return score.set_score()
        return score

    def calculate_score(self) -> "UserScore":
        return self.get_or_create_score().set_score()


class UserScore(models.Model):
    user = models.OneToOneField(
        "accounts.ProjectUser", on_delete=models.CASCADE, related_name="score"
    )
    completeness = models.FloatField(default=0)
    activity = models.FloatField(default=0)
    score = models.FloatField(default=0)

    def get_completeness(self) -> float:
        has_job = bool(self.user.job)
        has_expert_skills = self.user.skills.filter(level=4).exists()
        has_competent_skills = self.user.skills.filter(level=3).exists()
        has_rich_content = (
            "<img" in self.user.description or "<iframe" in self.user.description
        )
        description_length = len(self.user.description)
        return (
            int(has_job)
            + int(has_expert_skills)
            + int(has_competent_skills)
            + int(has_rich_content)
            + math.log10(1 + description_length)
        )

    def get_activity(self) -> float:
        last_activity = self.user.last_login
        if last_activity:
            weeks_since_last_activity = (
                timezone.localtime(timezone.now()) - last_activity
            ).days / 7
            return 5 / (1 + weeks_since_last_activity)
        return 0

    def set_score(self) -> "UserScore":
        completeness = self.get_completeness()
        activity = self.get_activity()
        score = completeness + activity
        self.completeness = completeness
        self.activity = activity
        self.score = score
        self.save()
        return self


class PrivacySettings(models.Model, HasOwner):
    class PrivacyChoices(models.TextChoices):
        HIDE = "hide"
        ORGANIZATION = "org"
        PUBLIC = "pub"

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
    email = models.CharField(
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
    _news_queryset = None
    _event_queryset = None
    _instruction_queryset = None

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

    def get_project_queryset(self) -> QuerySet["Project"]:
        if self._project_queryset is None:
            self._project_queryset = Project.objects.filter(
                publication_status=Project.PublicationStatus.PUBLIC
            )
        return self._project_queryset.distinct()

    def get_news_queryset(self) -> QuerySet["News"]:
        if self._news_queryset is None:
            self._news_queryset = News.objects.filter(visible_by_all=True)
        return self._news_queryset.distinct()

    def get_event_queryset(self) -> QuerySet["Event"]:
        if self._event_queryset is None:
            self._event_queryset = Event.objects.filter(visible_by_all=True)
        return self._event_queryset.distinct()

    def get_instruction_queryset(self) -> QuerySet["Instruction"]:
        if self._instruction_queryset is None:
            self._instruction_queryset = Instruction.objects.filter(visible_by_all=True)
        return self._instruction_queryset.distinct()

    def get_user_queryset(self) -> QuerySet["ProjectUser"]:
        if self._user_queryset is None:
            self._user_queryset = ProjectUser.objects.filter(
                privacy_settings__publication_status=PrivacySettings.PrivacyChoices.PUBLIC
            )
        return self._user_queryset.distinct()

    def get_people_group_queryset(self) -> QuerySet["PeopleGroup"]:
        if self._people_group_queryset is None:
            self._people_group_queryset = PeopleGroup.objects.filter(
                publication_status=PeopleGroup.PublicationStatus.PUBLIC
            )
        return self._people_group_queryset.distinct()

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

    def get_people_group_related_queryset(
        self, queryset: QuerySet, people_group_related_name: str = "people_group"
    ) -> QuerySet["PeopleGroup"]:
        return queryset.filter(
            **{
                f"{people_group_related_name}__publication_status": PeopleGroup.PublicationStatus.PUBLIC
            }
        )

    def get_news_related_queryset(
        self, queryset: QuerySet, news_related_name: str = "news"
    ) -> QuerySet["News"]:
        return queryset.filter(**{f"{news_related_name}__visible_by_all": True})

    def get_instruction_related_queryset(
        self, queryset: QuerySet, instruction_related_name: str = "instruction"
    ) -> QuerySet["Instruction"]:
        return queryset.filter(**{f"{instruction_related_name}__visible_by_all": True})

    def get_event_related_queryset(
        self, queryset: QuerySet, event_related_name: str = "event"
    ) -> QuerySet["Event"]:
        return queryset.filter(**{f"{event_related_name}__visible_by_all": True})

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
