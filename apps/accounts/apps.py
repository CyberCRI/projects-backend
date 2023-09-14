from django.apps import AppConfig


class AccountConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"

    def ready(self):
        """Register signals once the apps are loaded."""
        import apps.accounts.signals  # noqa
