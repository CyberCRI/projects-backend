from django.apps import AppConfig


class MistralConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "services.mistral"

    def ready(self):
        """Register signals once the apps are loaded."""
        import services.mistral.signals  # noqa
