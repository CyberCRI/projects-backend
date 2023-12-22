from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from apps.accounts.models import PeopleGroup, PrivacySettings


@receiver(post_save, sender="accounts.ProjectUser")
def create_privacy_settings(sender, instance, created, **kwargs):
    """Create the associated privacy settings at user's creation."""
    if created:
        PrivacySettings.objects.get_or_create(user=instance)


@receiver(post_save, sender="organizations.Organization")
def create_root_people_group(sender, instance, created, **kwargs):
    """Create the root people group at organization's creation."""
    PeopleGroup.update_or_create_root(instance)


@receiver(pre_delete, sender="accounts.PeopleGroup")
def delete_people_group_roles(sender, instance, **kwargs):
    """Delete the associated roles."""
    instance.groups.all().delete()
