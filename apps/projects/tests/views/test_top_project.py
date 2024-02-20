from django.urls import reverse
from parameterized import parameterized
from rest_framework import status

from apps.analytics.factories import StatFactory
from apps.commons.test import JwtAPITestCase
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory
from services.mixpanel.factories import MixpanelEventFactory


class ProjectTopTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()

    @parameterized.expand(
        [
            ("comments",),
            ("replies",),
            ("follows",),
            ("links",),
            ("files",),
            ("blog_entries",),
            ("description_length",),
            ("goals",),
            ("versions",),
        ]
    )
    def test_stats_ranking(self, stat_type):
        project_1 = ProjectFactory(organizations=[self.organization])
        project_2 = ProjectFactory(organizations=[self.organization])
        StatFactory(project=project_1, **{stat_type: 1})
        StatFactory(project=project_2, **{stat_type: 0})
        response = self.client.get(reverse("ProjectTop-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["count"], 2)
        self.assertEqual(content["results"][0]["id"], project_1.id)
        self.assertEqual(content["results"][1]["id"], project_2.id)

    def test_views_ranking(self):
        project_1 = ProjectFactory(organizations=[self.organization])
        project_2 = ProjectFactory(organizations=[self.organization])
        MixpanelEventFactory(project=project_1, organization=self.organization)
        response = self.client.get(reverse("ProjectTop-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["count"], 2)
        self.assertEqual(content["results"][0]["id"], project_1.id)
        self.assertEqual(content["results"][1]["id"], project_2.id)
