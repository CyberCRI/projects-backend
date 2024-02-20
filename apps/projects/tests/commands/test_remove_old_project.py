from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.utils import timezone

from apps.commons.test import JwtAPITestCase
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory
from apps.projects.models import Project


class CommandsTestCase(JwtAPITestCase):
    def test_remove_old_project(self):
        "Test remove_old_projects command."
        organization = OrganizationFactory()
        projects_to_delete = ProjectFactory.create_batch(
            3,
            organizations=[organization],
            deleted_at=timezone.now()
            - timedelta(days=settings.DELETED_PROJECT_RETENTION_DAYS + 1),
        )
        projects_to_keep = ProjectFactory.create_batch(
            3,
            organizations=[organization],
            deleted_at=timezone.now()
            - timedelta(days=settings.DELETED_PROJECT_RETENTION_DAYS - 1),
        )
        roles = [g.name for g in Group.objects.filter(projects__in=projects_to_delete)]
        call_command("remove_old_projects")
        self.assertEqual(len(Project.objects.deleted_projects()), 3)
        self.assertSetEqual(
            {p.id for p in Project.objects.deleted_projects()},
            {p.id for p in projects_to_keep},
        )
        self.assertFalse(Group.objects.filter(name__in=roles).exists())
