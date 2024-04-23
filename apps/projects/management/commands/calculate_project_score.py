from django.core.management.base import BaseCommand

from apps.projects.models import Project


class Command(BaseCommand):
    def handle(self, *args, **options):
        projects = Project.objects.all()
        for project in projects:
            project.calculate_score()
