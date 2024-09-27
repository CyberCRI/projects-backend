from projects.celery import app

from .utils import update_esco_data


@app.task(name="apps.skills.tasks.update_esco_data_task")
def update_esco_data_task():
    update_esco_data()
