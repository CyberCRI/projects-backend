import logging

from projects.celery import app

from .crisalid_bus import CrisalidEventEnum, CrisalidTypeEnum, crisalid_bus_client

logger = logging.getLogger(__name__)


@app.task(name=f"{__name__}.receive_researcher")
def receive_researcher(payload: dict):
    logger.info("receive %s", payload)


crisalid_bus_client.add_callback(
    CrisalidTypeEnum.RESEARCH, CrisalidEventEnum.CREATED, receive_researcher.apply
)
