from django.db import models


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
    updated_at: DateTimeField
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
    updated_at = models.DateTimeField(auto_now=True)
