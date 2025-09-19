from datetime import timedelta

from django.apps import apps
from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from apps.commons.utils import clear_memory
from projects.celery import app

from .models import Project, ProjectScore

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
    """calculate projects scores, get all projectsscore, calculate scores
    next we update all user/score during a bulk_update
    """

    bulk_update: list[ProjectScore] = []
    bulk_create: list[ProjectScore] = []

    for project in Project.objects.prefetch_related(
        "links", "files", "blog_entries", "locations", "goals", "follows"
    ).all():
        project.calculate_score()
        if project.score.pk:
            bulk_update.append(project.score)
        else:
            bulk_create.append(project.score)

    ProjectScore.objects.bulk_update(bulk_create)
    ProjectScore.objects.bulk_update(
        bulk_update, ["completeness", "popularity", "activity", "score"]
    )


@app.task(name="apps.projects.tasks.remove_old_project_versions")
def remove_old_project_versions():
    HistoricalProject.objects.filter(
        Q(
            history_date__lt=timezone.localtime(timezone.now())
            - timezone.timedelta(days=settings.PROJECT_VERSIONS_RETENTION_DAYS)
        )
        | Q(history_change_reason__isnull=True)
    ).delete()
