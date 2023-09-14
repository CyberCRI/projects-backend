from django.apps import AppConfig
from django.db.models.signals import post_migrate


class DeploysConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.deploys"

    def ready(self):
        from . import signals

        post_migrate.connect(signals.deploy, sender=self)
