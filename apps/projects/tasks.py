from django.core.management import call_command

from projects.celery import app

from .models import Project


@app.task(name="apps.projects.tasks.remove_old_projects")
def remove_old_projects():
    call_command("remove_old_projects")


@app.task(name="apps.projects.tasks.calculate_projects_scores")
def calculate_projects_scores():
    for project in Project.objects.all():
        project.calculate_score()
