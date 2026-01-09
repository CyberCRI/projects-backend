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
        self.client.stop()
        self.thread.join(3)
        self.thread = None


# dict registered client/thread by organization code
CLIENTS_ORGA_MAPS: dict[str, OrganizationClient] = {}


def start_crisalidbus(config: CrisalidConfig):
    with rlock:
        client = CLIENTS_ORGA_MAPS.get(config.organization.code)
        if client is not None:
            stop_crisalidbus(client.config)

        assert (
            config.active is True
        ), f"can't instanciate crisalidBus for {config.organization.code=}, active=False"

        client = OrganizationClient(config)
        CLIENTS_ORGA_MAPS[config.organization.code] = client
        client.start()


def stop_crisalidbus(config: CrisalidConfig):
    with rlock:
        if config.organization.code not in CLIENTS_ORGA_MAPS:
            return

        client = CLIENTS_ORGA_MAPS[config.organization.code]
        client.config = config
        client.stop()
        del CLIENTS_ORGA_MAPS[config.organization.code]


def initial_start_crisalidbus():
    """ "first start all thread (when server web is started)"""
    with rlock:
        for config in CrisalidConfig.objects.filter(active=True):
            start_crisalidbus(config)


# safe stop all crisalid bus
@atexit.register
def _stop_all_crisalid():
    with rlock:
        for client in list(CLIENTS_ORGA_MAPS.values()):
            stop_crisalidbus(client.config)
