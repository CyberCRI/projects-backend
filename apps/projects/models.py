import logging
import math
import os
from functools import reduce
from typing import TYPE_CHECKING, Any, List, Optional

import shortuuid as shortuuid
from django.conf import settings
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.postgres.fields import ArrayField
from django.core.cache import cache
from django.db import models, transaction
from django.db.models import QuerySet
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords, HistoricForeignKey

from apps.analytics.models import Stat
from apps.commons.enums import SDG, Language
from apps.commons.mixins import (
    DuplicableModel,
    HasMultipleIDs,
    HasOwner,
    HasPermissionsSetup,
    ProjectRelated,
)
from apps.commons.models import GroupData
from apps.commons.utils import get_write_permissions_from_subscopes
from services.translator.mixins import HasAutoTranslatedFields

from .exceptions import WrongProjectOrganizationError

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
    HasMultipleIDs,
    HasAutoTranslatedFields,
    HasPermissionsSetup,
    ProjectRelated,
    DuplicableModel,
    models.Model,
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

    project_query_string: str = ""
    organization_query_string: str = "organizations"

    slugified_fields: List[str] = ["title"]
    slug_prefix: str = "project"
    _auto_translated_fields: List[str] = ["title", "html:description", "purpose"]

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

    id = models.CharField(
        primary_key=True, auto_created=True, default=uuid_generator, max_length=8
    )
    title = models.CharField(max_length=255, verbose_name=_("title"))
    slug = models.SlugField(unique=True)
    outdated_slugs = ArrayField(models.SlugField(), default=list)
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
    tags = models.ManyToManyField(
        "skills.Tag",
        related_name="projects",
        blank=True,
        db_table="projects_project_skills_tags",  # avoid conflicts with old Tag model
    )
    sdgs = ArrayField(
        models.PositiveSmallIntegerField(choices=SDG.choices),
        len(SDG),
        default=list,
        blank=True,
        verbose_name=_("sustainable development goals"),
    )
    template = models.ForeignKey(
        "organizations.Template", on_delete=models.SET_NULL, null=True, blank=True
    )
    groups = models.ManyToManyField(Group, related_name="projects")
    history = HistoricalRecords(
        related_name="archive",
        m2m_fields=[tags, categories],
        excluded_fields=[
            f"{field.split(':', 1)[1] if ':' in field else field}_{lang}"
            for field in _auto_translated_fields
            for lang in settings.REQUIRED_LANGUAGES
        ],
    )
    duplicated_from = models.CharField(
        max_length=8, null=True, blank=True, default=None
    )
    permissions_up_to_date = models.BooleanField(default=False)
    objects = SoftDeleteManager()

    class Meta:
        write_only_subscopes = (
            ("review", "project's reviews"),
            ("comment", "project's comments"),
            ("follow", "project's follows"),
        )
        permissions = (
            ("view_projectmessage", "Can view project messages"),
            ("add_projectmessage", "Can add project messages"),
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
        self._related_organizations = None

    @classmethod
    def get_id_field_name(cls, object_id: Any) -> str:
        """Get the name of the field which contains the given ID."""
        if len(object_id) == 8:
            return "id"
        return "slug"

    @transaction.atomic
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if hasattr(self, "stat"):
            if self._original_description != self.description:
                self.stat.update_description_length()
            self.stat.update_versions()

    def delete(self, using=None, keep_parents=False):
        """
        Only soft-delete the project.

        The group roles are deleted in the `soft_delete` method to avoid
        any issue with the `get_instance_from_group`.
        """
        self.deleted_at = timezone.localtime(timezone.now())
        for group in [
            self.get_member_groups(),
            self.get_owner_groups(),
            self.get_reviewer_groups(),
        ]:
            group.delete()
        self.save()
        self._delete_auto_translated_fields()

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
                raise WrongProjectOrganizationError(
                    self.title, [o.name for o in organizations]
                )
            return sum(self.get_cached_views().get(o.code, 0) for o in organizations)
        return self.mixpanel_events.filter(organization__in=organizations).count()

    def get_related_project(self) -> Optional["Project"]:
        """Return the project related to this model."""
        return self

    def get_related_organizations(self) -> List["Organization"]:
        """Return the organizations related to this model."""
        if self._related_organizations is None:
            self._related_organizations = list(self.organizations.all())
        return self._related_organizations

    @classmethod
    def get_default_owners_permissions(cls) -> QuerySet[Permission]:
        content_type = ContentType.objects.get_for_model(cls)
        excluded_permissions = [
            f"{action}_{subscope}"
            for action in ["change", "delete", "add"]
            for subscope in ["review", "locked_project"]
        ]
        return Permission.objects.filter(content_type=content_type).exclude(
            codename__in=excluded_permissions
        )

    @classmethod
    def get_default_reviewers_permissions(cls) -> QuerySet[Permission]:
        content_type = ContentType.objects.get_for_model(cls)
        return Permission.objects.filter(content_type=content_type)

    @classmethod
    def get_default_members_permissions(cls) -> QuerySet[Permission]:
        content_type = ContentType.objects.get_for_model(cls)
        return Permission.objects.filter(
            content_type=content_type,
            codename__in=[
                "view_project",
                "view_projectmessage",
                "add_projectmessage",
                "duplicate_project",
            ],
        )

    def setup_permissions(self, user: Optional["ProjectUser"] = None):
        """Setup the group with default permissions."""
        reviewers_permissions = self.get_default_reviewers_permissions()
        owners_permissions = self.get_default_owners_permissions()
        members_permissions = self.get_default_members_permissions()

        reviewers = self.setup_group_object_permissions(
            self.get_reviewers(), reviewers_permissions
        )
        owners = self.setup_group_object_permissions(
            self.get_owners(), owners_permissions
        )
        members = self.setup_group_object_permissions(
            self.get_members(), members_permissions
        )
        reviewer_groups = self.setup_group_object_permissions(
            self.get_reviewer_groups(), reviewers_permissions
        )
        owner_groups = self.setup_group_object_permissions(
            self.get_owner_groups(), owners_permissions
        )
        member_groups = self.setup_group_object_permissions(
            self.get_member_groups(), members_permissions
        )

        if user:
            owners.users.add(user)
        self.groups.add(
            owners, reviewers, members, owner_groups, reviewer_groups, member_groups
        )
        self.permissions_up_to_date = True
        self.save(update_fields=["permissions_up_to_date"])

    def get_owners(self) -> Group:
        """Return the owners group."""
        return self.get_or_create_group(GroupData.Role.OWNERS)

    def get_reviewers(self) -> Group:
        """Return the reviewers group."""
        return self.get_or_create_group(GroupData.Role.REVIEWERS)

    def get_members(self) -> Group:
        """Return the members group."""
        return self.get_or_create_group(GroupData.Role.MEMBERS)

    def get_member_groups(self) -> Group:
        """Return the members group."""
        return self.get_or_create_group(GroupData.Role.MEMBER_GROUPS)

    def get_owner_groups(self) -> Group:
        """Return the members group."""
        return self.get_or_create_group(GroupData.Role.OWNER_GROUPS)

    def get_reviewer_groups(self) -> Group:
        """Return the members group."""
        return self.get_or_create_group(GroupData.Role.REVIEWER_GROUPS)

    @property
    def owners(self) -> QuerySet["ProjectUser"]:
        return self.get_owners().users

    @property
    def reviewers(self) -> QuerySet["ProjectUser"]:
        return self.get_reviewers().users

    @property
    def members(self) -> QuerySet["ProjectUser"]:
        return self.get_members().users

    @property
    def member_groups(self) -> QuerySet["PeopleGroup"]:
        return self.get_member_groups().people_groups

    @property
    def owner_groups(self) -> QuerySet["PeopleGroup"]:
        return self.get_owner_groups().people_groups

    @property
    def reviewer_groups(self) -> QuerySet["PeopleGroup"]:
        return self.get_reviewer_groups().people_groups

    @property
    def member_groups_users(self) -> QuerySet["ProjectUser"]:
        return self.get_member_groups().users

    @property
    def owner_groups_users(self) -> QuerySet["ProjectUser"]:
        return self.get_owner_groups().users

    @property
    def reviewer_groups_users(self) -> QuerySet["ProjectUser"]:
        return self.get_reviewer_groups().users

    def set_role_group_members(self, role_group: Group):
        people_groups = role_group.people_groups.all()
        people_groups_users = [
            people_group.get_all_members() for people_group in people_groups
        ]
        people_groups_users = reduce(
            lambda x, y: x.union(y), people_groups_users, set()
        )
        role_group.users.set(people_groups_users)

    def set_role_groups_members(self):
        for group in [
            self.get_member_groups(),
            self.get_owner_groups(),
            self.get_reviewer_groups(),
        ]:
            self.set_role_group_members(group)

    def get_all_members(self) -> QuerySet["ProjectUser"]:
        """Return the all members."""
        return (
            self.owners.all() | self.reviewers.all() | self.members.all()
        ).distinct()

    def get_all_groups(self) -> QuerySet["PeopleGroup"]:
        """Return all groups."""
        return (
            self.member_groups.all()
            | self.owner_groups.all()
            | self.reviewer_groups.all()
        ).distinct()

    def _get_score_instance(self) -> "ProjectScore":
        try:
            return self.score
        except Project.score.RelatedObjectDoesNotExist:
            self.score = ProjectScore(project=self)
            return self.score

    def get_or_create_score(self) -> "ProjectScore":
        score = self._get_score_instance()
        if not score.pk:
            score.set_score()
            score.save()
        return score

    def calculate_score(self) -> "ProjectScore":
        score = self._get_score_instance()
        score.set_score()
        return score

    @transaction.atomic
    def duplicate(self, owner: Optional["ProjectUser"] = None) -> "Project":
        header = self.header_image.duplicate(owner) if self.header_image else None
        project = Project.objects.create(
            title=self.title,
            header_image=header,
            description=self.description,
            purpose=self.purpose,
            is_locked=self.is_locked,
            is_shareable=self.is_shareable,
            publication_status=Project.PublicationStatus.PRIVATE,
            life_status=self.life_status,
            language=self.language,
            sdgs=self.sdgs,
            template=self.template,
            duplicated_from=self.id,
        )
        project.setup_permissions(user=owner)
        project.categories.set(self.categories.all())
        project.organizations.set(self.organizations.all())
        project.tags.set(self.tags.all())
        for image in self.images.all():
            new_image = image.duplicate(owner)
            if new_image is not None:
                project.images.add(new_image)
                for identifier in [self.pk, self.slug]:
                    project.description = project.description.replace(
                        f"/v1/project/{identifier}/image/{image.pk}/",
                        f"/v1/project/{project.pk}/image/{new_image.pk}/",
                    )
        project.save()
        for blog_entry in self.blog_entries.all():
            blog_entry.duplicate(project, self, owner)
        for announcement in self.announcements.all():
            announcement.duplicate(project)
        for location in self.locations.all():
            location.duplicate(project)
        for goal in self.goals.all():
            goal.duplicate(project)
        for link in self.links.all():
            link.duplicate(project)
        for file in self.files.all():
            file.duplicate(project)
        Stat.objects.create(project=project)
        return project


class ProjectScore(models.Model, ProjectRelated):
    project = models.OneToOneField(
        "projects.Project", on_delete=models.CASCADE, related_name="score"
    )
    completeness = models.FloatField(default=0)
    popularity = models.FloatField(default=0)
    activity = models.FloatField(default=0)
    score = models.FloatField(default=0)

    def get_related_project(self) -> Project:
        return self.project

    def get_related_organizations(self) -> List["Organization"]:
        return self.project.get_related_organizations()

    def get_completeness(self) -> float:
        has_ressources = self.project.links.exists() or self.project.files.exists()
        has_blogs = self.project.blog_entries.exists()
        has_goals = self.project.goals.exists()
        has_location = self.project.locations.exists()
        has_rich_content = (
            "<img" in self.project.description
            or "<iframe" in self.project.description
            or any(
                "<img" in blog_entry.content or "<iframe" in blog_entry.content
                for blog_entry in self.project.blog_entries.all()
            )
        )
        description_length = len(self.project.description)
        blog_entries_length = sum(
            len(blog_entry.content) + len(blog_entry.title)
            for blog_entry in self.project.blog_entries.all()
        )
        return (
            int(has_ressources)
            + int(has_blogs)
            + int(has_goals)
            + int(has_location)
            + int(has_rich_content)
            + math.log10(1 + description_length + blog_entries_length)
        )

    def get_popularity(self) -> float:
        follows_count = math.log(self.project.follows.count() + 1, 4)
        views_count = math.log(self.project.get_views() + 1, 8)
        comments_length = sum(
            len(comment.content) for comment in self.project.comments.all()
        )
        return math.log10(1 + comments_length) + follows_count + views_count

    def get_activity(self) -> float:
        last_activity = self.project.updated_at
        weeks_since_last_activity = (
            timezone.localtime(timezone.now()) - last_activity
        ).days / 7
        return 10 / (1 + weeks_since_last_activity)

    def set_score(self) -> "ProjectScore":
        completeness = self.get_completeness()
        popularity = self.get_popularity()
        activity = self.get_activity()
        score = completeness + popularity + activity
        self.completeness = completeness
        self.popularity = popularity
        self.activity = activity
        self.score = score
        return self


class LinkedProject(models.Model, ProjectRelated):
    """Store unidirectional link between projects.

    Attributes
    ----------
    project: ForeignKey
        `Project` being linked.
    target: ForeignKey
        `Project` the first one is being linked to.
    """

    project_query_string: str = "target"
    organization_query_string: str = "target__organizations"

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="linked_to"
    )
    target = HistoricForeignKey(
        Project, on_delete=models.CASCADE, related_name="linked_projects"
    )
    history = HistoricalRecords()

    class Meta:
        unique_together = ("project", "target")

    def get_related_project(self) -> Optional["Project"]:
        """Return the projects related to this model."""
        return self.target

    def get_related_organizations(self) -> List["Organization"]:
        """Return the organizations related to this model."""
        return self.target.get_related_organizations()


class BlogEntry(
    HasAutoTranslatedFields,
    ProjectRelated,
    DuplicableModel,
    models.Model,
):
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

    _auto_translated_fields: List[str] = ["title", "html:content"]

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
        verbose_name_plural = "Blog entries"

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

    def get_related_project(self) -> Optional["Project"]:
        """Return the projects related to this model."""
        return self.project

    def get_related_organizations(self) -> List["Organization"]:
        """Return the organizations related to this model."""
        return self.project.get_related_organizations()

    def duplicate(
        self,
        project: "Project",
        initial_project: Optional["Project"] = None,
        owner: Optional["ProjectUser"] = None,
    ) -> "BlogEntry":
        blog_entry = BlogEntry.objects.create(
            project=project,
            title=self.title,
            content=self.content,
        )
        for image in self.images.all():
            new_image = image.duplicate(owner)
            if new_image is not None:
                blog_entry.images.add(new_image)
                for identifier in [initial_project.pk, initial_project.slug]:
                    blog_entry.content = blog_entry.content.replace(
                        f"/v1/project/{identifier}/blog-entry-image/{image.pk}/",
                        f"/v1/project/{project.pk}/blog-entry-image/{new_image.pk}/",
                    )
        blog_entry.created_at = self.created_at
        blog_entry.save()
        return blog_entry


class Goal(
    HasAutoTranslatedFields,
    ProjectRelated,
    DuplicableModel,
    models.Model,
):
    """Goal of a project.

    Attributes
    ----------
    id: Charfield
        UUID4 used as the model's PK.
    project: ForeignKey
        Project following this Goal.
    title: Charfield
        Title of the Goal.
    description: TextField
        Description of the Goal.
    deadline_at: BooleanField, optional
        Deadline of the Goal.
    status: CharField,
        Status of the Goal.
    """

    _auto_translated_fields: List[str] = ["title", "html:description"]

    class GoalStatus(models.TextChoices):
        NONE = "na"
        ONGOING = "ongoing"
        COMPLETE = "complete"
        CANCEL = "cancel"

    project = models.ForeignKey(
        "projects.Project", on_delete=models.CASCADE, related_name="goals"
    )
    title = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    deadline_at = models.DateField(null=True)
    status = models.CharField(
        max_length=24, choices=GoalStatus.choices, default=GoalStatus.NONE
    )

    @transaction.atomic
    def save(self, *args, **kwargs):
        create = self.pk is None
        super().save(*args, **kwargs)
        if create and hasattr(self.project, "stat"):
            self.project.stat.update_goals()

    @transaction.atomic
    def delete(self, using=None, keep_parents=False):
        project = self.project
        super().delete(using, keep_parents)
        if hasattr(project, "stat"):
            project.stat.update_goals()

    def get_related_organizations(self) -> List["Organization"]:
        """Return the organizations related to this model."""
        return self.project.get_related_organizations()

    def get_related_project(self) -> Optional["Project"]:
        """Return the project related to this model."""
        return self.project

    def duplicate(self, project: "Project") -> "Goal":
        return Goal.objects.create(
            project=project,
            title=self.title,
            description=self.description,
            deadline_at=self.deadline_at,
            status=self.status,
        )


class Location(
    HasAutoTranslatedFields,
    ProjectRelated,
    DuplicableModel,
    models.Model,
):
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

    _auto_translated_fields: List[str] = ["title", "description"]

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

    def get_related_project(self) -> Optional["Project"]:
        """Return the projects related to this model."""
        return self.project

    def get_related_organizations(self) -> List["Organization"]:
        """Return the organizations related to this model."""
        return self.project.get_related_organizations()

    def duplicate(self, project: "Project") -> "Location":
        return Location.objects.create(
            project=project,
            title=self.title,
            description=self.description,
            lat=self.lat,
            lng=self.lng,
            type=self.type,
        )


class ProjectMessage(
    HasAutoTranslatedFields,
    ProjectRelated,
    HasOwner,
    models.Model,
):
    """
    A message in a project.

    Attributes
    ----------
    project: ForeignKey projects.Project
        Project this message belong to.
    author: ForeignKey accounts.ProjectUser
        Author of the message.
    reply_on: ForeignKey self
        Message this one is replying to (if any).
    content: TextField
        Content of the message.
    created_at: DateTimeField
        Date of creation of this message.
    updated_at: DateTimeField
        Date of the last change made to the message.
    deleted_at: DateTimeField
        Date the message was soft-deleted.
    images: ManyToManyField files.Image
        Images used by the message.
    """

    _auto_translated_fields: List[str] = ["html:content"]

    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="messages",
    )
    author = models.ForeignKey(
        "accounts.ProjectUser",
        on_delete=models.CASCADE,
        related_name="project_messages",
    )
    reply_on = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        default=None,
        null=True,
        related_name="replies",
    )
    content = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, default=None)
    images = models.ManyToManyField("files.Image", related_name="project_messages")

    def __str__(self):
        return f"Project message from {self.author} on {self.project}"

    def get_related_project(self) -> "Project":
        """Return the projects related to this model."""
        return self.project

    def get_related_organizations(self) -> List["Organization"]:
        """Return the organizations related to this model."""
        return self.project.get_related_organizations()

    class Meta:
        ordering = ["-created_at"]

    def soft_delete(self):
        self.deleted_at = timezone.localtime(timezone.now())
        self.save()
        self._delete_auto_translated_fields()

    def get_owner(self):
        """Get the owner of the object."""
        return self.author

    def is_owned_by(self, user: "ProjectUser") -> bool:
        """Whether the given user is the owner of the object."""
        return self.author == user


class ProjectTab(
    HasAutoTranslatedFields,
    ProjectRelated,
    models.Model,
):
    """A tab in the project page.

    Attributes
    ----------
    project: ForeignKey
        Project this tab belong to.
    type: CharField
        Type of the tab. Can be either "text" or "blog".
    title: CharField
        Title of the tab.
    description: TextField
        Description of the tab.
    """

    _auto_translated_fields: List[str] = ["title", "html:description"]

    class TabType(models.TextChoices):
        """Type of a tab."""

        TEXT = "text"
        BLOG = "blog"

    project = models.ForeignKey(
        "projects.Project", on_delete=models.CASCADE, related_name="additional_tabs"
    )
    type = models.CharField(
        max_length=32, choices=TabType.choices, default=TabType.TEXT
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=255, blank=True)
    images = models.ManyToManyField("files.Image", related_name="project_tabs")

    def get_related_project(self) -> Project:
        """Return the projects related to this model."""
        return self.project

    def get_related_organizations(self) -> List["Organization"]:
        """Return the organizations related to this model."""
        return self.project.get_related_organizations()


class ProjectTabItem(
    HasAutoTranslatedFields,
    ProjectRelated,
    models.Model,
):
    """An item in a project tab.

    Attributes
    ----------
    project: ForeignKey
        Project this item belong to.
    title: CharField
        Title of the item.
    content: TextField
        Content of the item.
    """

    project_query_string: str = "tab__project"
    organization_query_string: str = "tab__project__organizations"

    _auto_translated_fields: List[str] = ["title", "html:content"]

    tab = models.ForeignKey(
        "projects.ProjectTab", on_delete=models.CASCADE, related_name="items"
    )
    title = models.CharField(max_length=255)
    content = models.TextField(blank=True)
    images = models.ManyToManyField("files.Image", related_name="project_tab_items")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def get_related_project(self) -> Project:
        """Return the projects related to this model."""
        return self.tab.project

    def get_related_organizations(self) -> List["Organization"]:
        """Return the organizations related to this model."""
        return self.tab.project.get_related_organizations()
