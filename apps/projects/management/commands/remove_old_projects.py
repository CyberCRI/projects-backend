from django.core.management.base import BaseCommand

from apps.projects.tasks import remove_old_projects


class Command(BaseCommand):
    def handle(self, *args, **options):
        remove_old_projects()
