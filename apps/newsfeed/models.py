from typing import TYPE_CHECKING, List

from django.db import models

from apps.commons.enums import Language
from apps.commons.mixins import HasOwner, OrganizationRelated
from services.translator.mixins import HasAutoTranslatedFields

if TYPE_CHECKING:
    from apps.accounts.models import ProjectUser
    from apps.organizations.models import Organization


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
    news: ForeignKey
        News in the newsfeed.
    type: CharField
        Type of the object.
    """

    class NewsfeedType(models.TextChoices):
        """Type of the news in the newsfeed."""

        PROJECT = "project"
        ANNOUNCEMENT = "announcement"
        NEWS = "news"

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
    news = models.ForeignKey(
        "newsfeed.News",
        on_delete=models.CASCADE,
        null=True,
        related_name="newsfeed_news",
    )
    type = models.CharField(
        max_length=50, choices=NewsfeedType.choices, default=NewsfeedType.PROJECT
    )


class News(HasAutoTranslatedFields, OrganizationRelated, models.Model):
    """News instance.

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
        Date of the news' publication.
    groups: ManyToManyField
        Groups which have access to the news.
    created_at: DateTimeField
        Date of creation of this news.
    updated_at: DateTimeField
        Date of the last change made to the news.
    visible_by_all: BooleanField
        If the news is visible by all the users, connected or not, member of a group or not.
    """

    _auto_translated_fields: List[str] = ["title", "html:content"]

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
    visible_by_all = models.BooleanField(default=False)
    images = models.ManyToManyField("files.Image", related_name="news")

    def get_related_organizations(self):
        return [self.organization]


class Instruction(HasAutoTranslatedFields, OrganizationRelated, HasOwner, models.Model):
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
    visible_by_all: BooleanField
        If the news is visible by all the users, connected or not, member of a group or not.
    """

    _auto_translated_fields: List[str] = ["title", "html:content"]

    owner = models.ForeignKey(
        "accounts.ProjectUser",
        related_name="owned_instructions",
        null=True,
        on_delete=models.SET_NULL,
    )
    title = models.CharField(max_length=255, verbose_name=("title"))
    content = models.TextField(blank=True, default="")
    publication_date = models.DateTimeField()
    people_groups = models.ManyToManyField(
        "accounts.PeopleGroup", related_name="instructions", blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    language = models.CharField(
        max_length=2, choices=Language.choices, default=Language.default()
    )
    organization = models.ForeignKey(
        "organizations.Organization",
        related_name="instructions",
        on_delete=models.CASCADE,
    )
    has_to_be_notified = models.BooleanField(default=False)
    notified = models.BooleanField(default=False)
    visible_by_all = models.BooleanField(default=False)
    images = models.ManyToManyField("files.Image", related_name="instructions")

    def get_related_organizations(self):
        return [self.organization]

    def get_owner(self):
        """Get the owner of the object."""
        return self.owner

    def is_owned_by(self, user: "ProjectUser") -> bool:
        """Whether the given user is the owner of the object."""
        return self.owner == user


class Event(HasAutoTranslatedFields, OrganizationRelated, models.Model):
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
    visible_by_all: BooleanField
        If the news is visible by all the users, connected or not, member of a group or not.
    """

    _auto_translated_fields: List[str] = ["title", "html:content"]

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
    visible_by_all = models.BooleanField(default=False)
    images = models.ManyToManyField("files.Image", related_name="events")

    def get_related_organizations(self) -> List["Organization"]:
        return [self.organization]
