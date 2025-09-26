from projects.celery import app

from .crisalid_bus import CrisalidEventEnum, CrisalidTypeEnum, crisalid_bus_client


@app.task(name=f"{__name__}.receive_researcher")
def receive_researcher(payload: dict): ...


crisalid_bus_client.add_callback(
    CrisalidTypeEnum.RESEARCH, CrisalidEventEnum.CREATED, receive_researcher.apply
)
