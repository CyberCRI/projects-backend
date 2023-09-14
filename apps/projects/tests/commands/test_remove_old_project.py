from datetime import timedelta

from django.conf import settings
from django.core.management import call_command
from django.utils import timezone

from apps.commons.test import JwtAPITestCase
from apps.projects.factories import ProjectFactory
from apps.projects.models import Project


class CommandsTestCase(JwtAPITestCase):
    def generate_data(self):
        projects = ProjectFactory.create_batch(size=3)
        for project in projects:
            project.delete()

        projects[0].deleted_at = timezone.now() - timedelta(
            days=settings.DELETED_PROJECT_RETENTION_DAYS + 1
        )
        projects[0].save()

    def test_remove_old_project(self):
        "Test remove_old_projects command."
        self.generate_data()
        call_command("remove_old_projects")
        self.assertEqual(len(Project.objects.deleted_projects()), 2)
