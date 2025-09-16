from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from .models import TermsAndConditions


@receiver(pre_delete, sender="organizations.Organization")
def delete_organization_roles(sender, instance, **kwargs):
    """Delete the associated roles."""
    instance.groups.all().delete()


@receiver(post_save, sender="organizations.Organization")
def create_terms_and_conditions(sender, instance, created, **kwargs):
    """Create the associated terms and conditions at user's creation."""
    if created:
        TermsAndConditions.objects.get_or_create(organization=instance)
