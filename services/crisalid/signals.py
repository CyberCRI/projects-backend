from django.conf import settings
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from services.crisalid.bus.runner import start_crisalidbus, stop_crisalidbus
from services.crisalid.models import CrisalidConfig


@receiver(post_save, sender=CrisalidConfig)
def on_save(sender, instance, **kwargs):
    if not settings.ENABLE_CRISALID_BUS:
        return
    if instance.active:
        start_crisalidbus(instance)
    else:
        stop_crisalidbus(instance)


@receiver(post_delete, sender=CrisalidConfig)
def on_delete(sender, instance, **kwargs):
    stop_crisalidbus(instance)
