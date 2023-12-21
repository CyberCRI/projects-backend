import logging
import os
from functools import reduce
from typing import TYPE_CHECKING, Any, Iterable, List, Optional

import shortuuid as shortuuid
from django.conf import settings
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import ArrayField
from django.core.cache import cache
from django.db import models, transaction
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from guardian.shortcuts import assign_perm
from simple_history.models import HistoricalRecords, HistoricForeignKey

from apps.commons.db.abc import (
    HasMultipleIDs,
    OrganizationRelated,
    PermissionsSetupModel,
    ProjectRelated,
)
from apps.commons.utils.permissions import get_write_permissions_from_subscopes
from apps.misc.models import SDG, Language, Tag, WikipediaTag

logger = logging.getLogger(__file__)

if TYPE_CHECKING:
    from apps.accounts.models import PeopleGroup, ProjectUser
    from apps.organizations.models import Organization


def uuid_generator() -> str:
    """Generate a short UUID of only 8 character.

    Used for backward compatibility.
    """
    return shortuuid.ShortUUID().random(length=8)


class SoftDeleteManager(models.Manager):
    """Exclude by default soft-deleted Projects."""

    def get_queryset(self):
        """Exclude by default soft-deleted Projects."""
        return super().get_queryset().filter(deleted_at=None)

    def all_with_delete(self, pk=None):
        """Retrieve all projects, or the one corresponding to `pk` if given."""
        if pk is None:
            return super().get_queryset()
        return super().get_queryset().get(pk=pk)

    def deleted_projects(self):
        """Retrieve all soft-deleted projects."""
        return super().get_queryset().exclude(deleted_at=None)


class Project(
    HasMultipleIDs, PermissionsSetupModel, ProjectRelated, OrganizationRelated
):
    """Main model of the app, represent a user project

    Attributes
    ----------
    id: Charfield
        UUID4 used as the model's PK.
    title: Charfield
        Title of the project.
    header_image: ForeignKey, optional
        Image used as header background of the project.
    description: CharField
        Description of the project
    purpose: TextField
        Purpose of the project.
    is_locked: BooleanField
        Whether the project is locked or not.
    is_shareable: BooleanField
        Whether the project is shareable or not.
    publication_status: CharField
        Visibility of the project.
    life_status: CharField
        Status of the project.
    language: CharField
        Language of the project.
    created_at: DateTimeField
        Date of creation of this project.
    updated_at: DateTimeField
        Date of the last change made to the project.
    deleted_at: DateTimeField
        Date the project was soft-deleted.
    images: ManyToManyField
        Images used by the project.
    category: ForeignKey
        Category of the project.
    organizations: ManyToManyField
        Organizations this project is part of.
    wikipedia_tags: ManyToManyField
        Tags this project is referred to.
    sdgs: ArrayField
        UN Sustainable Development Goals this project try to achieve.
    history: HistoricalRecords
        History of this project.
    """

    class PublicationStatus(models.TextChoices):
        """Visibility setting of a project."""

        PUBLIC = "public"
        PRIVATE = "private"
        ORG = "org"

    class LifeStatus(models.TextChoices):
        """State of a project."""

        RUNNING = "running"
        COMPLETED = "completed"
        CANCELED = "canceled"
        TO_REVIEW = "toreview"

    class DefaultGroup(models.TextChoices):
        """Default permission groups of a project."""

        MEMBERS = "members"
        OWNERS = "owners"
        REVIEWERS = "reviewers"
        PEOPLE_GROUPS = "people_groups"

    id = models.CharField(
        primary_key=True, auto_created=True, default=uuid_generator, max_length=8
    )
    title = models.CharField(max_length=255, verbose_name=_("title"))
    slug = models.SlugField(unique=True)
    header_image = models.ForeignKey(
        "files.Image",
        on_delete=models.SET_NULL,
        null=True,
        related_name="project_header",
    )
    description = models.TextField(blank=True, default="")
    purpose = models.TextField(blank=True, verbose_name=_("main goal"))
    is_locked = models.BooleanField(default=False)
    is_shareable = models.BooleanField(default=False)
    publication_status = models.CharField(
        max_length=10,
        choices=PublicationStatus.choices,
        default=PublicationStatus.PRIVATE,
        verbose_name=_("visibility"),
    )
    life_status = models.CharField(
        max_length=10,
        choices=LifeStatus.choices,
        default=LifeStatus.RUNNING.value,
        verbose_name=_("life status"),
    )
    language = models.CharField(
        max_length=2, choices=Language.choices, default=Language.default()
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True)
    categories = models.ManyToManyField(
        "organizations.ProjectCategory",
        related_name="projects",
        verbose_name=_("categories"),
    )
    images = models.ManyToManyField("files.Image", related_name="projects")
    organizations = models.ManyToManyField(
        "organizations.Organization", related_name="projects"
    )
    wikipedia_tags = models.ManyToManyField(
        WikipediaTag, related_name="projects", verbose_name=_("wikipedia tags")
    )
    organization_tags = models.ManyToManyField(
        Tag, verbose_name=_("organizational tags")
    )
    sdgs = ArrayField(
        models.PositiveSmallIntegerField(choices=SDG.choices),
        len(SDG),
        default=list,
        blank=True,
        verbose_name=_("sustainable development goals"),
    )
    main_category = HistoricForeignKey(
        "organizations.ProjectCategory",
        on_delete=models.SET_NULL,
        null=True,
        verbose_name=_("main category"),
    )
    groups = models.ManyToManyField(Group, related_name="projects")
    history = HistoricalRecords(
        related_name="archive",
        m2m_fields=[wikipedia_tags, organization_tags, categories],
    )
    objects = SoftDeleteManager()

    class Meta:
        write_only_subscopes = (
            ("review", "project's reviews"),
            ("comment", "project's comments"),
            ("follow", "project's follows"),
        )
        permissions = (
            ("lock_project", "Can lock and unlock a project"),
            ("duplicate_project", "Can duplicate a project"),
            ("change_locked_project", "Can update a locked project"),
            *get_write_permissions_from_subscopes(write_only_subscopes),
        )

    @property
    def url(self) -> str:
        return os.path.join(
            self.organizations.first().website_url, f"project/{self.pk}/"
        )

    @property
    def content_type(self) -> ContentType:
        return ContentType.objects.get_for_model(Project)

    def __init__(self, *args, **kwargs):
        super(Project, self).__init__(*args, **kwargs)
        self._original_description = self.description

    @classmethod
    def get_id_field_name(cls, object_id: Any) -> str:
        """Get the name of the field which contains the given ID."""
        if len(object_id) == 8:
            return "id"
        return "slug"

    def get_slug(self) -> str:
        if self.slug == "":
            raw_slug = slugify(self.title[0:46])
            if len(raw_slug) <= 8:
                raw_slug = f"project-{raw_slug}"  # Prevent clashes with ids
            slug = raw_slug
            same_slug_count = 0
            while Project.objects.all_with_delete().filter(slug=slug).exists():
                same_slug_count += 1
                slug = f"{raw_slug}-{same_slug_count}"
            return slug
        return self.slug

    @transaction.atomic
    def save(self, *args, **kwargs):
        self.slug = self.get_slug()
        super().save(*args, **kwargs)
        if hasattr(self, "stat"):
            if self._original_description != self.description:
                self.stat.update_description_length()
            self.stat.update_versions()

    def delete(self, using=None, keep_parents=False):
        """Only soft-delete the project."""
        self.deleted_at = timezone.now()
        self.save()

    @transaction.atomic
    def hard_delete(self):
        """Hard-delete the project."""
        self.groups.all().delete()
        super(Project, self).delete()

    def restore(self):
        """Restore a soft-deleted project."""
        self.deleted_at = None
        self.save()

    def set_cached_views(self, timeout: int = 60 * settings.CACHE_PROJECT_VIEWS):
        if settings.ENABLE_CACHE:
            key = f"project.{self.id}.views"
            views_cache = {
                organization.code: self.mixpanel_events.filter(
                    organization=organization
                ).count()
                for organization in self.organizations.all()
            }
            views_cache["_total"] = self.mixpanel_events.count()
            cache.set(key, views_cache, timeout)

    def get_cached_views(self):
        """Caches all views of the project."""
        key = f"project.{self.id}.views"
        if key not in cache.keys("*"):  # noqa: SIM118
            self.set_cached_views()
        return cache.get(key)

    @classmethod
    def get_queryset_cached_views(cls, projects: models.QuerySet["Project"]):
        """Caches all views of the project."""
        keys = [f"project.{project.id}.views" for project in projects]
        cache_keys = cache.keys("*")
        absent_projects = [
            project
            for project in projects
            if f"project.{project.id}.views" not in cache_keys
        ]
        for project in absent_projects:
            project.set_cached_views()
        return cache.get_many(keys)

    @classmethod
    def get_queryset_total_views(cls, projects: models.QuerySet["Project"]):
        """Caches all views of the project."""
        if settings.ENABLE_CACHE:
            views = cls.get_queryset_cached_views(projects)
            return {key.split(".")[1]: value["_total"] for key, value in views.items()}
        return {project.id: project.mixpanel_events.count() for project in projects}

    @classmethod
    def get_queryset_organization_views(
        cls, projects: models.QuerySet["Project"], organization: "Organization"
    ):
        """Caches all views of the project."""
        if settings.ENABLE_CACHE:
            views = cls.get_queryset_cached_views(projects)
            return {
                key.split(".")[1]: value.get(organization.code, 0)
                for key, value in views.items()
            }
        return {
            project.id: project.mixpanel_events.filter(
                organization=organization
            ).count()
            for project in projects
        }

    def get_views(self) -> int:
        """Return the project's views on the whole platform."""
        if settings.ENABLE_CACHE:
            return self.get_cached_views().get("_total", 0)
        return self.mixpanel_events.count()

    def get_views_organizations(self, organizations: List["Organization"]) -> int:
        """Return the project's views inside the given organization.

        If you plan on using this method multiple time, prefetch `organizations`
        to avoid any n+1 performance issue.
        """
        if settings.ENABLE_CACHE:
            if not organizations:
                return self.get_views()
            if not any(o in self.organizations.all() for o in organizations):
                raise ValueError(f"{self} does not belong to one of {organizations}")
            return sum(self.get_cached_views().get(o.code, 0) for o in organizations)
        return self.mixpanel_events.filter(organization__in=organizations).count()

    def get_related_projects(self) -> List["Project"]:
        """Return the project related to this model."""
        return [self]

    def get_related_organizations(self) -> List["Organization"]:
        """Return the organizations related to this model."""
        return self.organizations.all()

    def get_default_owners_permissions(self) -> Iterable[Permission]:
        excluded_permissions = [
            f"{action}_{subscope}"
            for action in ["change", "delete", "add"]
            for subscope in ["review", "locked_project"]
        ]
        return Permission.objects.filter(content_type=self.content_type).exclude(
            codename__in=excluded_permissions
        )

    def get_default_reviewers_permissions(self) -> Iterable[Permission]:
        return Permission.objects.filter(content_type=self.content_type)

    def get_default_members_permissions(self) -> Iterable[Permission]:
        return Permission.objects.filter(
            content_type=self.content_type,
            codename="view_project",
        )

    def setup_permissions(self, user: Optional["ProjectUser"] = None):
        """Setup the project with default permissions."""
        owners = self.get_owners()
        owners.permissions.clear()
        for permission in self.get_default_owners_permissions():
            assign_perm(permission, owners, self)

        reviewers = self.get_reviewers()
        reviewers.permissions.clear()
        for permission in self.get_default_reviewers_permissions():
            assign_perm(permission, reviewers, self)

        members = self.get_members()
        members.permissions.clear()
        for permission in self.get_default_members_permissions():
            assign_perm(permission, members, self)

        member_people_groups = self.get_people_groups()
        member_people_groups.permissions.clear()
        for permission in self.get_default_members_permissions():
            assign_perm(permission, member_people_groups, self)

        if user:
            owners.users.add(user)
        self.groups.add(owners, reviewers, members)
        self.permissions_up_to_date = True
        # Saving is also mandatory to trigger indexing in Algolia
        self.save(update_fields=["permissions_up_to_date"])

    def remove_duplicated_roles(self):
        """Remove duplicated roles in the group."""
        self.members.set(
            self.members.exclude(
                pk__in=self.reviewers.values_list("pk", flat=True)
            ).exclude(pk__in=self.owners.values_list("pk", flat=True))
        )
        self.owners.set(
            self.owners.exclude(pk__in=self.reviewers.values_list("pk", flat=True))
        )

    def get_or_create_group(self, name: str) -> Group:
        """Return the group with the given name."""
        group, created = Group.objects.get_or_create(
            name=f"{self.content_type.model}:#{self.pk}:{name}",
        )
        if created:
            self.groups.add(group)
        return group

    def get_owners(self) -> Group:
        """Return the owners group."""
        return self.get_or_create_group(self.DefaultGroup.OWNERS)

    def get_reviewers(self) -> Group:
        """Return the reviewers group."""
        return self.get_or_create_group(self.DefaultGroup.REVIEWERS)

    def get_members(self) -> Group:
        """Return the members group."""
        return self.get_or_create_group(self.DefaultGroup.MEMBERS)

    def get_people_groups(self) -> Group:
        """Return the members group."""
        return self.get_or_create_group(self.DefaultGroup.PEOPLE_GROUPS)

    @property
    def owners(self) -> List["ProjectUser"]:
        return self.get_owners().users

    @property
    def reviewers(self) -> List["ProjectUser"]:
        return self.get_reviewers().users

    @property
    def members(self) -> List["ProjectUser"]:
        return self.get_members().users

    @property
    def member_people_groups(self) -> List["PeopleGroup"]:
        return self.get_people_groups().people_groups

    @property
    def member_people_groups_members(self) -> List["ProjectUser"]:
        return self.get_people_groups().users

    def set_people_group_members(self):
        people_groups = self.member_people_groups.all()
        people_groups_users = [
            people_group.get_all_members() for people_group in people_groups
        ]
        people_groups_users = reduce(
            lambda x, y: x.union(y), people_groups_users, set()
        )
        self.member_people_groups_members.set(people_groups_users)

    def get_all_members(self) -> List["ProjectUser"]:
        """Return the all members."""
        return (
            self.owners.all() | self.reviewers.all() | self.members.all()
        ).distinct()


class LinkedProject(models.Model, ProjectRelated, OrganizationRelated):
    """Store unidirectional link between projects.

    Attributes
    ----------
    project: ForeignKey
        `Project` being linked.
    target: ForeignKey
        `Project` the first one is being linked to.
    """

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="linked_to"
    )
    target = HistoricForeignKey(
        Project, on_delete=models.CASCADE, related_name="linked_projects"
    )
    history = HistoricalRecords()

    class Meta:
        unique_together = ("project", "target")

    def save(self, **kwargs):
        """Block Projects from linking to themselves."""
        if self.project.id == self.target.id:
            raise ValueError(f"Project {self.project.id} can't be linked to himself")
        super().save(**kwargs)

    def get_related_projects(self) -> List["Project"]:
        """Return the projects related to this model."""
        return [self.target]

    def get_related_organizations(self) -> List["Organization"]:
        """Return the organizations related to this model."""
        return self.target.get_related_organizations()


class BlogEntry(models.Model, ProjectRelated, OrganizationRelated):
    """A blog entry in a project.

    Attributes
    ----------
    project: ForeignKey
        Project this blog entry belong to.
    title: CharField
        Title of the blog entry.
    content: CharField
        Title of the blog entry.
    images: ManyToManyField
        Images used by the entry.
    created_at: DateTimeField
        Date of creation of this blog entry.
    updated_at: DateTimeField
        Date of the last change made to the blog entry.
    """

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="blog_entries"
    )
    title = models.CharField(max_length=255)
    content = models.TextField(blank=True)
    images = models.ManyToManyField("files.Image", related_name="blog_entries")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    @transaction.atomic
    def save(self, *args, **kwargs):
        create = self.pk is None
        super().save(*args, **kwargs)
        if create and hasattr(self.project, "stat"):
            self.project.stat.update_blog_entries()

    @transaction.atomic
    def delete(self, using=None, keep_parents=False):
        project = self.project
        super().delete(using, keep_parents)
        if hasattr(project, "stat"):
            project.stat.update_blog_entries()

    def get_related_projects(self) -> List["Project"]:
        """Return the projects related to this model."""
        return [self.project]

    def get_related_organizations(self) -> List["Organization"]:
        """Return the organizations related to this model."""
        return self.project.get_related_organizations()


class Location(models.Model, ProjectRelated, OrganizationRelated):
    """A project location on Earth.

    Attributes
    ----------
    id: Charfield
        UUID4 used as the model's PK.
    project: ForeignKey
        Project at this location.
    title: Charfield
        Title of the location.
    description: TextField
        Description of the location.
    lat: FloatField
        Latitude of the location.
    lng: FloatField
        Longitude of the location.
    type: CharField
        Type of the location (team or impact).
    """

    class LocationType(models.TextChoices):
        """Type of a location."""

        TEAM = "team"
        IMPACT = "impact"

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="locations"
    )
    title = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    lat = models.FloatField()
    lng = models.FloatField()
    type = models.CharField(
        max_length=6,
        choices=LocationType.choices,
        default=LocationType.TEAM,
    )

    def get_related_projects(self) -> List["Project"]:
        """Return the projects related to this model."""
        return [self.project]

    def get_related_organizations(self) -> List["Organization"]:
        """Return the organizations related to this model."""
        return self.project.get_related_organizations()
