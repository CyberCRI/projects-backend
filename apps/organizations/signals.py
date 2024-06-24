from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from .models import Faq


@receiver(pre_delete, sender="organizations.Organization")
def delete_organization_roles(sender, instance, **kwargs):
    """Delete the associated roles."""
    instance.groups.all().delete()


@receiver(post_save, sender="organizations.Organization")
def create_organization_faq(sender, instance, created, **kwargs):
    """Create a FAQ for the organization."""
    if instance.faq is None:
        instance.faq = Faq.objects.create(title="", content="")
        instance.save()


@receiver(pre_delete, sender="organizations.Faq")
def create_new_organization_faq(sender, instance, **kwargs):
    """Create a new FAQ for the organization."""
    instance.organization.faq = Faq.objects.create(title="", content="")
    instance.organization.save()
