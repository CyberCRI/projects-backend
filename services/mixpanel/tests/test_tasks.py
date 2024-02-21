from unittest.mock import patch

from django.test import TestCase

from apps.projects.factories import ProjectFactory
from apps.projects.models import Project
from services.mixpanel.models import MixpanelEvent
from services.mixpanel.tasks import get_new_mixpanel_events


class MixpanelServiceTestCase(TestCase):
    def side_effect(self, projects_list):
        def inner(*args, **kwargs):
            results = [
                "".join(
                    [
                        '{"event":"page_viewed","properties":{"time":1660595601,"$insert_id":"',
                        project.id,
                        "-",
                        project.organizations.first().code,
                        '","organization":{"code":"',
                        project.organizations.first().code,
                        '","id":"',
                        str(project.organizations.first().id),
                        '","name":"',
                        project.organizations.first().name,
                        '"},"project":{"id":"',
                        project.id,
                        '"}}}',
                    ]
                )
                for project in projects_list
            ]
            return "\n".join(results) + ","

        return inner

    @patch("mixpanel_utils.MixpanelUtils.request")
    def test_get_new_mixpanel_events(self, mocked):
        projects = ProjectFactory.create_batch(
            5, publication_status=Project.PublicationStatus.PUBLIC
        )
        mocked.side_effect = self.side_effect(projects)
        get_new_mixpanel_events()
        self.assertEqual(MixpanelEvent.objects.count(), 5)
        for project in projects:
            self.assertEqual(project.get_views(), 1)
