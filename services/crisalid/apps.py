import threading

from django.apps import AppConfig


class CrisalidConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "services.crisalid"

    def __init__(self, *ar, **kw):
        super().__init__(*ar, **kw)
        self.__thread_crisalid_bus = None

    def ready(self):
        # initialize crisalid bus

        import services.crisalid.tasks  # noqa: F401
        from services.crisalid.crisalid_bus import crisalid_bus_client

        # target is connect function in crisalidbus
        self.__thread_crisalid_bus = threading.Thread(
            target=crisalid_bus_client.connect,
            name="CrisalidBus",
            daemon=True,
        )

        # start thread
        self.__thread_crisalid_bus.start()

    def __delete__(self):
        from .crisalid_bus import crisalid_bus_client

        crisalid_bus_client.disconnect()
        # wait 3 seconds to stop thread (the thread is daemon, so no realy need this)
        self.__thread_crisalid_bus.join(3)
