from django.db.models.signals import pre_delete
from django.dispatch import receiver


@receiver(pre_delete, sender="organizations.Organization")
def delete_organization_roles(sender, instance, **kwargs):
    """Delete the associated roles."""
    instance.groups.all().delete()
