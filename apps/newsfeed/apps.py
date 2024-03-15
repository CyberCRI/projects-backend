from django.apps import AppConfig


class NewsfeedConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.newsfeed"

    def ready(self):
        """Register signals once the apps are loaded."""
        import apps.newsfeed.signals  # noqa
