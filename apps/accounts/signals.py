from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.accounts.models import PrivacySettings
from apps.accounts.utils import get_default_group


@receiver(post_save, sender="accounts.ProjectUser")
def add_user_to_public_group(sender, instance, created, **kwargs):
    """Post-create user signal that adds the user to the default group."""
    if created:
        instance.groups.add(get_default_group())


@receiver(post_save, sender="accounts.ProjectUser")
def create_privacy_settings(sender, instance, created, **kwargs):
    """Create the associated privacy settings at user's creation."""
    if created:
        PrivacySettings.objects.get_or_create(user=instance)


@receiver(post_save, sender="organizations.Organization")
def create_root_people_group(sender, instance, created, **kwargs):
    """Create the root people group at organization's creation."""
    instance.get_or_create_root_people_group()
