from typing import TYPE_CHECKING, List, Optional

from django.db import models, transaction
from django.utils import timezone
from simple_history.models import HistoricalRecords, HistoricForeignKey

from apps.commons.mixins import HasOwner, ProjectRelated
from services.translator.mixins import HasAutoTranslatedFields

if TYPE_CHECKING:
    from apps.accounts.models import ProjectUser
    from apps.organizations.models import Organization
    from apps.projects.models import Project


class Follow(HasOwner, ProjectRelated, models.Model):
    """Represent a user following a project.

    Attributes
    ----------
    id: Charfield
        UUID4 used as the model's PK.
    project: ForeignKey
        Project followed.
    follower: ForeignKey
        ProjectUser following the project.
    created_at: DateTimeField
        Date of creation of the object.
    updated_at: DateTimeField
        Date of the last change made to the object.
    history: HistoricalRecords
        History of the object.
    """

    project = models.ForeignKey(
        "projects.Project", on_delete=models.CASCADE, related_name="follows"
    )
    follower = models.ForeignKey(
        "accounts.ProjectUser",
        on_delete=models.CASCADE,
        related_name="follows",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    def __str__(self):
        return f"{self.project} - {self.follower}"

    @transaction.atomic
    def save(self, *args, **kwargs):
        create = self.pk is None
        super().save(*args, **kwargs)
        if create and hasattr(self.project, "stat"):
            self.project.stat.update_follows()

    @transaction.atomic
    def delete(self, using=None, keep_parents=False):
        project = self.project
        super().delete(using, keep_parents)
        if hasattr(project, "stat"):
            project.stat.update_follows()

    def is_owned_by(self, user: "ProjectUser") -> bool:
        """Whether the given user is the owner of the object."""
        return self.follower == user

    def get_owner(self):
        """Get the owner of the object."""
        return self.follower

    def get_related_project(self) -> Optional["Project"]:
        """Return the project related to this model."""
        return self.project

    def get_related_organizations(self) -> List["Organization"]:
        """Return the organizations related to this model."""
        return self.project.get_related_organizations()

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "follower"], name="unique_follow"
            )
        ]


class Comment(HasAutoTranslatedFields, HasOwner, ProjectRelated, models.Model):
    """A comment written by a user about some project, may be an answer to another comment.

    Attributes
    ----------
    id: Charfield
        UUID4 used as the model's PK.
    project: ForeignKey
        Project the comment is about.
    author: ForeignKey
        Author of the comment.
    ref: ForeignKey
        Comment this comment answer to. None for top-level comment.
    content: TextField
        Content of the comment.
    created_at: DateTimeField
        Date of creation of the object.
    updated_at: DateTimeField
        Date of the last change made to the object.
    deleted_at: DateTimeField, optional
        Date the comment was deleted.
    deleted_by: ForeignKey, optional
        User who deleted the comment.
    history: HistoricalRecords
        History of the object.
    """

    auto_translated_fields: List[str] = ["html:content"]

    project = HistoricForeignKey(
        "projects.Project", on_delete=models.CASCADE, related_name="comments"
    )
    author = models.ForeignKey(
        "accounts.ProjectUser",
        on_delete=models.CASCADE,
        related_name="comments",
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
    deleted_by = models.ForeignKey(
        "accounts.ProjectUser", on_delete=models.SET_NULL, null=True, default=None
    )
    images = models.ManyToManyField("files.Image", related_name="comments")
    history = HistoricalRecords()

    def __str__(self):
        return str(self.content)

    @transaction.atomic
    def save(self, *args, **kwargs):
        create = self.pk is None
        super().save(*args, **kwargs)
        if create and hasattr(self.project, "stat"):
            self.project.stat.update_comments_and_replies()

    @transaction.atomic
    def soft_delete(self, by: "ProjectUser"):
        self.deleted_at = timezone.localtime(timezone.now())
        self.deleted_by = by
        self.save()
        if hasattr(self.project, "stat"):
            self.project.stat.update_comments_and_replies()
        self._delete_auto_translated_fields()

    def is_owned_by(self, user: "ProjectUser") -> bool:
        """Whether the given user is the owner of the object."""
        return self.author == user

    def get_owner(self):
        """Get the owner of the object."""
        return self.author

    def get_related_project(self) -> Optional["Project"]:
        """Return the projects related to this model."""
        return self.project

    def get_related_organizations(self) -> List["Organization"]:
        """Return the organizations related to this model."""
        return self.project.get_related_organizations()

    class Meta:
        ordering = ["-created_at"]


class Review(HasAutoTranslatedFields, HasOwner, ProjectRelated, models.Model):
    """A review made by a User about a Project.

    Attributes
    ----------
    id: Charfield
        UUID4 used as the model's PK.
    project: ForeignKey
        Project at this location.
    reviewer: ForeignKey
        ProjectUser who wrote the review.
    title: Charfield
        Title of the location.
    description: TextField
        Description of the location.
    created_at: DateTimeField
        Date of creation of the review.
    updated_at: DateTimeField
        Date of the last change made to the review.
    """

    auto_translated_fields: List[str] = ["html:description", "title"]

    description = models.TextField(blank=True)
    title = models.CharField(max_length=100)
    project = models.ForeignKey(
        "projects.Project", on_delete=models.CASCADE, related_name="reviews"
    )
    reviewer = models.ForeignKey(
        "accounts.ProjectUser", on_delete=models.CASCADE, related_name="reviews"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self.title)

    def is_owned_by(self, user: "ProjectUser") -> bool:
        """Whether the given user is the owner of the object."""
        return self.reviewer == user

    def get_owner(self):
        """Get the owner of the object."""
        return self.reviewer

    def get_related_project(self) -> Optional["Project"]:
        """Return the projects related to this model."""
        return self.project

    def get_related_organizations(self) -> List["Organization"]:
        """Return the organizations related to this model."""
        return self.project.get_related_organizations()
