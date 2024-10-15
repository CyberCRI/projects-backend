from datetime import timedelta

from django.apps import apps
from django.conf import settings
from django.utils import timezone

from apps.commons.test import JwtAPITestCase
from apps.projects.factories import ProjectFactory, ProjectHistoryFactory
from apps.projects.tasks import remove_old_project_versions

HistoricalProject = apps.get_model("projects", "HistoricalProject")


class RemoveOldProjectVersionsTaskTestCase(JwtAPITestCase):
    def test_remove_old_project_versions(self):
        project = ProjectFactory()
        recent_history_change_reason = ProjectHistoryFactory(
            history_relation=project,
            id=project.id,
            history_date=timezone.localtime(timezone.now())
            - timedelta(days=settings.PROJECT_VERSIONS_RETENTION_DAYS - 1),
            history_change_reason="Updated: title",
        )
        ProjectHistoryFactory(
            history_relation=project,
            id=project.id,
            history_date=timezone.localtime(timezone.now())
            - timedelta(days=settings.PROJECT_VERSIONS_RETENTION_DAYS - 1),
            history_change_reason=None,
        )

        ProjectHistoryFactory(
            history_relation=project,
            id=project.id,
            history_date=timezone.localtime(timezone.now())
            - timedelta(days=settings.PROJECT_VERSIONS_RETENTION_DAYS + 1),
            history_change_reason=None,
        )
        ProjectHistoryFactory(
            history_relation=project,
            id=project.id,
            history_date=timezone.localtime(timezone.now())
            - timedelta(days=settings.PROJECT_VERSIONS_RETENTION_DAYS + 1),
            history_change_reason="Updated: title",
        )
        queryset = HistoricalProject.objects.filter(history_relation=project)
        self.assertGreaterEqual(queryset.count(), 4)
        remove_old_project_versions()
        queryset = HistoricalProject.objects.filter(history_relation=project)
        self.assertEqual(queryset.count(), 1)
        self.assertEqual(queryset.get(), recent_history_change_reason)
