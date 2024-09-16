from projects.celery import app

from .utils import update_esco_data


@app.task(name="services.esco.tasks.update_esco_data_task")
def update_esco_data_task():
    update_esco_data()
