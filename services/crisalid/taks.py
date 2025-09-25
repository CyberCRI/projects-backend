from projects.celery import app

from .crisalid_bus import CrisalidEventEnum, CrisalidTypeEnum, callback


@callback(CrisalidTypeEnum.RESEARCH, CrisalidEventEnum.CREATED)
@app.task(name=f"{__name__}.receive_research")
def receive_research(payload: dict): ...
