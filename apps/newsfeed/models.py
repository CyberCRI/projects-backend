from typing import TYPE_CHECKING, List

from django.db import models

from apps.commons.models import OrganizationRelated
from apps.misc.models import Language

if TYPE_CHECKING:
    from apps.organizations.models import Organization


class News(models.Model, OrganizationRelated):
    """News isntance.

    Attributes
    ----------
    ----------
    id: Charfield
        UUID4 used as the model's PK.
    title: CharField
        Title of the news.
    content: TextField
        Content of the news.
    header_image: ForeignKey
        Image in the news.
    publication_date: DateTimeField
        Date of teh news' publication.
    groups: ManyToManyField
        Groups which have access to the news.
    created_at: DateTimeField
        Date of creation of this project.
    updated_at: DateTimeField
        Date of the last change made to the project.
    """

    title = models.CharField(max_length=255, verbose_name=("title"))
    content = models.TextField(blank=True, default="")
    header_image = models.ForeignKey(
        "files.Image",
        on_delete=models.SET_NULL,
        null=True,
        related_name="news_header",
    )
    publication_date = models.DateTimeField()
    people_groups = models.ManyToManyField("accounts.PeopleGroup", related_name="news")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    language = models.CharField(
        max_length=2, choices=Language.choices, default=Language.default()
    )
    organization = models.ForeignKey(
        "organizations.Organization", related_name="news", on_delete=models.CASCADE
    )

    def get_related_organizations(self):
        return [self.organization]

class Instruction(models.Model, OrganizationRelated):
    """Instruction instance.
    Attributes
    ----------
    ----------
    id: Charfield
        UUID4 used as the model's PK.
    title: CharField
        Title of the instruction.
    content: TextField
        Content of the instruction.
    publication_date: DateTimeField
        Date of the instruction's publication.
    groups: ManyToManyField
        Groups which have access to the instruction.
    created_at: DateTimeField
        Date of creation of this instruction.
    updated_at: DateTimeField
        Date of the last change made to the instruction.
    has_to_be_notified: BooleanField
        If a notification has to be sent to the groups.
    notified: BooleanField
        If a notification has already been sent.
    """

    title = models.CharField(max_length=255, verbose_name=("title"))
    content = models.TextField(blank=True, default="")
    publication_date = models.DateTimeField()
    people_groups = models.ManyToManyField("accounts.PeopleGroup", related_name="instructions", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    language = models.CharField(
        max_length=2, choices=Language.choices, default=Language.default()
    )
    organization = models.ForeignKey(
        "organizations.Organization", related_name="instructions", on_delete=models.CASCADE
    )
    has_to_be_notified = models.BooleanField(default=False)
    notified = models.BooleanField(default=False)
    
    def get_related_organizations(self):
        return [self.organization]

class Newsfeed(models.Model):
    """Newsfeed of the application.

    Attributes
    ----------
    ----------
    id: Charfield
        UUID4 used as the model's PK.
    project: ForeignKey
        Project in the newsfeed.
    announcement: ForeignKey
        Announcement in the newsfeed.
    type: CharField
        Type of the object.
    """

    class NewsfeedType(models.TextChoices):
        """Type of the news in the newsfeed."""

        PROJECT = "project"
        ANNOUNCEMENT = "announcement"

    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        null=True,
        related_name="newsfeed_project",
    )
    announcement = models.ForeignKey(
        "announcements.Announcement",
        on_delete=models.CASCADE,
        null=True,
        related_name="newsfeed_announcement",
    )
    type = models.CharField(
        max_length=50, choices=NewsfeedType.choices, default=NewsfeedType.PROJECT
    )


class Event(models.Model, OrganizationRelated):
    """News isntance.

    Attributes
    ----------
    ----------
    id: Charfield
        UUID4 used as the model's PK.
    title: CharField
        Title of the event.
    content: TextField
        Content of the event.
    event_date: DateTimeField
        Date of teh event' publication.
    groups: ManyToManyField
        Groups which have access to the event.
    created_at: DateTimeField
        Date of creation of this project.
    updated_at: DateTimeField
        Date of the last change made to the project.
    """

    title = models.CharField(max_length=255, verbose_name=("title"))
    content = models.TextField(blank=True, default="")
    event_date = models.DateTimeField()
    people_groups = models.ManyToManyField(
        "accounts.PeopleGroup", related_name="events"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    organization = models.ForeignKey(
        "organizations.Organization", related_name="events", on_delete=models.CASCADE
    )

    def get_related_organizations(self) -> List["Organization"]:
        return [self.organization]
