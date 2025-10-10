import os
from functools import cached_property

from celery import Celery, bootsteps
from kombu import Consumer, Queue

CRISALID_BUS = {
    "host": os.getenv("CRISALID_BUS_HOST"),
    "port": os.getenv("CRISALID_BUS_PORT"),
    "user": os.getenv("CRISALID_BUS_USER"),
    "password": os.getenv("CRISALID_BUS_PASSWORD"),
}

CELERY_BROKER_URL = f"amqp://{CRISALID_BUS['user']}:{CRISALID_BUS['password']}@{CRISALID_BUS['host']}:{CRISALID_BUS['port']}//"
os.environ["CELERY_BROKER_URL"] = CELERY_BROKER_URL
crisalid_app = Celery("crisalid", broker=CELERY_BROKER_URL)
crisalid_app.config_from_object("django.conf:settings", namespace="CELERY")

# Set the timezone and enable UTC
crisalid_app.conf.timezone = "Europe/Paris"
crisalid_app.conf.enable_utc = True


class CrisalidConsumer(bootsteps.ConsumerStep):
    QUEUES = (
        "crisalid-ikg-harvesting-events",
        "crisalid-ikg-people",
        "crisalid-ikg-publications",
        "crisalid-ikg-structures",
    )

    @cached_property
    def _crisalid_bus_client(self):
        import services.crisalid.crisalid_event  # noqa: F401
        from services.crisalid.crisalid_bus import crisalid_bus_client

        return crisalid_bus_client

    def get_consumers(self, channel):
        return [
            Consumer(
                channel,
                queues=[Queue(k, k) for k in CrisalidConsumer.QUEUES],
                callbacks=[self.handle_message],
                accept=["json"],
            )
        ]

    def handle_message(self, body, message):
        self._crisalid_bus_client._dispatch(body)


crisalid_app.steps["consumer"].add(CrisalidConsumer)
