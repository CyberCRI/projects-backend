from django.core.management import call_command

from projects.celery import app


@app.task(name="apps.projects.tasks.remove_old_projects")
def remove_old_projects():
    call_command("remove_old_projects")
