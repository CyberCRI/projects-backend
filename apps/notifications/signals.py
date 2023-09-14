from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.accounts.models import ProjectUser

from .models import NotificationSettings


@receiver(post_save, sender=ProjectUser)
def create_notification_settings(sender, instance, created, **kwargs):
    """Create the associated notification settings at user's creation."""
    if created:
        NotificationSettings.objects.create(user=instance)
