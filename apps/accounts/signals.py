from django.db.models.signals import m2m_changed, post_save, pre_delete
from django.dispatch import receiver

from apps.accounts.models import PeopleGroup, PrivacySettings, ProjectUser


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


@receiver(pre_delete, sender="accounts.PeopleGroup")
def change_people_group_children_parent(sender, instance, **kwargs):
    """Change the parent of the children groups."""
    instance.children.update(parent=instance.parent)


@receiver(m2m_changed, sender=ProjectUser.groups.through)
def clear_user_querysets_cache(sender, instance, action, **kwargs):
    """Create the associated search object at user's creation."""
    if isinstance(instance, ProjectUser):
        instance.clear_querysets_cache()
