from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.announcements.models import Announcement
from apps.newsfeed.models import News, Newsfeed
from apps.projects.models import Project


@receiver(post_save, sender=Project)
def create_or_update_newsfeed_project(sender, instance, created, **kwargs):
    """Create a newsfeed object upon a project's creation or update the updated_at field."""
    feed, created = Newsfeed.objects.update_or_create(
        project=instance,
        type=Newsfeed.NewsfeedType.PROJECT,
    )
    if instance.deleted_at is not None:
        feed.delete()


@receiver(post_save, sender=Announcement)
def create_or_update_newsfeed_announcement(sender, instance, created, **kwargs):
    """Create a newsfeed object upon an announcement's creation or update the updated_at field."""
    feed, created = Newsfeed.objects.update_or_create(
        announcement=instance,
        type=Newsfeed.NewsfeedType.ANNOUNCEMENT,
    )
    if instance.project.deleted_at is not None:
        feed.delete()


@receiver(post_save, sender=News)
def create_or_update_newsfeed_news(sender, instance, created, **kwargs):
    """Create a newsfeed object upon a news' creation or update the updated_at field."""
    feed, created = Newsfeed.objects.update_or_create(
        news=instance,
        type=Newsfeed.NewsfeedType.NEWS,
    )
