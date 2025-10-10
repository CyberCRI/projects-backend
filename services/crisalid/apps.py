from django.apps import AppConfig
from django.conf import settings


class CrisalidConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "services.crisalid"

    def __init__(self, *ar, **kw):
        super().__init__(*ar, **kw)

    def ready(self):
        # initialize crisalid bus

        if settings.ENABLE_CRISALID_BUS:
            import services.crisalid.tasks  # noqa: F401
            from services.crisalid.crisalid_bus import start_thread

            start_thread()

    def __delete__(self):
        if settings.ENABLE_CRISALID_BUS:
            from .crisalid_bus import stop_thread

            stop_thread()
