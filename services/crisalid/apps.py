from django.apps import AppConfig


class CrisalidConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "services.crisalid"

    def __init__(self, *ar, **kw):
        super().__init__(*ar, **kw)

    def ready(self):
        import services.crisalid.tasks  # noqa: F401
