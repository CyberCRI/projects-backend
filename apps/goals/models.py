from typing import TYPE_CHECKING, List, Optional

from django.db import models, transaction

from apps.commons.models import DuplicableModel, OrganizationRelated, ProjectRelated

if TYPE_CHECKING:
    from apps.organizations.models import Organization
    from apps.projects.models import Project


class Goal(models.Model, ProjectRelated, OrganizationRelated, DuplicableModel):
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

    def duplicate(self, project: "Project"):
        return Goal.objects.create(
            project=project,
            title=self.title,
            description=self.description,
            deadline_at=self.deadline_at,
            status=self.status,
        )
