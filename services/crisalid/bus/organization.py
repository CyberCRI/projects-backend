import atexit
import logging
import threading

from services.crisalid.bus.client import CrisalidBusClient
from services.crisalid.models import CrisalidConfig

rlock = threading.RLock()


class OrganizationClient:
    def __init__(self, config: CrisalidConfig):
        self.config = config
        self.client = CrisalidBusClient(self.config)
        self.logger = logging.getLogger(config.organization.code)
        self.thread = None

    @property
    def name(self):
        return self.config.organization.code

    def start(self):
        thread_name = f"[{self.name}]CrisalidBus"
        assert self.thread is None, f"can't start twice {thread_name}"

        self.logger.info("Start thread %s", thread_name)
        self.thread = threading.Thread(
            target=self.client.connect,
            name=thread_name,
            daemon=True,
        )
        self.thread.start()

    def stop(self):
        self.logger.info("Stop thread %s", self.name)
        if self.thread is None:
            return
        self.client.disconnect()
        self.thread.join(3)
        self.thread = None


organization_maps: dict[str, OrganizationClient] = {}


def start_crisalidbus(config: CrisalidConfig):
    with rlock:
        client = organization_maps.get(config.organization.code)
        if client is None:
            client = OrganizationClient(config)
            organization_maps[config.organization.code] = client
        else:
            client.stop()
            client.config = config

        client.start()


def stop_crisalidbus(config: CrisalidConfig):
    with rlock:
        client = organization_maps.get(config.organization.code)
        if client is None:
            return
        client.config = config
        client.stop()


def delete_crisalidbus(config: CrisalidConfig):
    with rlock:
        client = organization_maps.get(config.organization.code)
        if client is None:
            return
        client.stop()
        del organization_maps[config.organization.code]


# safe stop all crisalid bus
@atexit.register
def _stop_all_crisalid():
    with rlock:
        for client in list(organization_maps.values()):
            delete_crisalidbus(client.config)
