from django.apps import AppConfig


class SearchConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.search"

    def ready(self):
        """Register signals once the apps are loaded."""
        import apps.search.signals  # noqa
