from django.core.management.base import BaseCommand

from apps.projects.tasks import calculate_projects_scores


class Command(BaseCommand):
    def handle(self, *args, **options):
        calculate_projects_scores()
