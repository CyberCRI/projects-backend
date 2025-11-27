from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from services.crisalid.apps import CrisalidConfig
from services.crisalid.bus.organization import (
    remove_crisalidbus,
    start_crisalidbus,
)


@receiver(post_save, sender=CrisalidConfig)
def on_save(sender, instance, **kwargs):
    if instance.active:
        start_crisalidbus(instance)
    else:
        remove_crisalidbus(instance)


@receiver(post_delete, sender=CrisalidConfig)
def on_delete(sender, instance, **kwargs):
    remove_crisalidbus(instance)
