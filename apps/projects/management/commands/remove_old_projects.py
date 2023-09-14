from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils.timezone import now

from apps.projects.models import Project


class Command(BaseCommand):
    def handle(self, *args, **options):
        max_date = now() - timedelta(days=settings.DELETED_PROJECT_RETENTION_DAYS)
        for project in Project.objects.deleted_projects().filter(
            deleted_at__lt=max_date
        ):
            project.hard_delete()
