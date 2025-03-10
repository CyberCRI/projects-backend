from datetime import timedelta

from django.apps import apps
from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from apps.commons.utils import clear_memory
from projects.celery import app

from .models import Project

HistoricalProject = apps.get_model("projects", "HistoricalProject")


@app.task(name="apps.projects.tasks.remove_old_projects")
@clear_memory
def remove_old_projects():
    max_date = timezone.now() - timedelta(days=settings.DELETED_PROJECT_RETENTION_DAYS)
    for project in Project.objects.deleted_projects().filter(deleted_at__lt=max_date):
        project.hard_delete()


@app.task(name="apps.projects.tasks.calculate_projects_scores")
@clear_memory
def calculate_projects_scores():
    for project in Project.objects.all():
        project.calculate_score()


@app.task(name="apps.projects.tasks.remove_old_project_versions")
def remove_old_project_versions():
    HistoricalProject.objects.filter(
        Q(
            history_date__lt=timezone.localtime(timezone.now())
            - timezone.timedelta(days=settings.PROJECT_VERSIONS_RETENTION_DAYS)
        )
        | Q(history_change_reason__isnull=True)
    ).delete()
