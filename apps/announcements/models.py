from typing import TYPE_CHECKING, List, Optional

from django.db import models

from apps.commons.models import OrganizationRelated, ProjectRelated

if TYPE_CHECKING:
    from apps.organizations.models import Organization
    from apps.projects.models import Project


class Announcement(models.Model, ProjectRelated, OrganizationRelated):
    """Information about an announcement working on a Project.

    Attributes
    ----------
    id: Charfield
        UUID4 used as the model's PK.
    project: ForeignKey
        Project at the announcement is for.
    title: Charfield
        Title of the announcement.
    description: TextField
        Description of the announcement's work.
    status: CharField
        Status of the announcement.
    deadline: DateField
        Deadline of the work.
    is_remunerated: BooleanField
        Whether the announcement is paid of not.
    created_at: DateTimeField
        Date of creation of the announcement.
    updated_at: DateTimeField
        Date of the last change made to the announcement.
    """

    class AnnouncementType(models.TextChoices):
        NONE = ("na", "Not applicable")
        PARTICIPANT = ("participant", "Participant")
        JOB = ("job", "Job")
        TRAINEESHIP = ("traineeship", "Traineeship")

    class AnnouncementStatus(models.TextChoices):
        OPEN = "open"
        CLOSED = "closed"

    project = models.ForeignKey(
        "projects.Project", on_delete=models.CASCADE, related_name="announcements"
    )
    description = models.TextField(blank=True)
    title = models.CharField(max_length=100)
    type = models.CharField(
        max_length=12, choices=AnnouncementType.choices, default=AnnouncementType.NONE
    )
    status = models.CharField(
        max_length=12,
        choices=AnnouncementStatus.choices,
        default=AnnouncementStatus.OPEN,
    )
    deadline = models.DateField(null=True)
    is_remunerated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_related_organizations(self) -> List["Organization"]:
        """Return the organizations related to this model."""
        return self.project.get_related_organizations()

    def get_related_project(self) -> Optional["Project"]:
        """Return the project related to this model."""
        return self.project

    def __str__(self):
        return str(self.title)
