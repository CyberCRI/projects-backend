from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.announcements.models import Announcement
from apps.newsfeed.models import Newsfeed
from apps.projects.models import Project


@receiver(post_save, sender=Project)
def create_or_update_newsfeed_project(sender, instance, created, **kwargs):
    """Create a newsfeed object upon a project's creation or update the updated_at field."""
    if created:
        Newsfeed.objects.get_or_create(
            project=instance,
            type=Newsfeed.NewsfeedType.PROJECT,
            updated_at=instance.updated_at,
        )
    else:
        Newsfeed.objects.filter(project=instance).update(updated_at=instance.updated_at)


@receiver(post_save, sender=Announcement)
def create_or_update_newsfeed_announcement(sender, instance, created, **kwargs):
    """Create a newsfeed object upon an announcement's creation or update the updated_at field."""
    if created:
        Newsfeed.objects.get_or_create(
            announcement=instance,
            type=Newsfeed.NewsfeedType.ANNOUNCEMENT,
            updated_at=instance.updated_at,
        )
    else:
        Newsfeed.objects.filter(announcement=instance).update(
            updated_at=instance.updated_at
        )
