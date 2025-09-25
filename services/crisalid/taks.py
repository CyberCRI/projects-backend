from projects.celery import app

from .crisalid_bus import CrisalidEventEnum, CrisalidTypeEnum, crisalid_bus_client


@app.task(name=f"{__name__}.receive_research")
def receive_research(payload: dict): ...


crisalid_bus_client.add_callback(
    CrisalidTypeEnum.RESEARCH, CrisalidEventEnum.CREATED, receive_research.apply
)
