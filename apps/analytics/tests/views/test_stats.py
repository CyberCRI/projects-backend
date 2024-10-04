import datetime

from django.urls import reverse
from django.utils.timezone import make_aware
from parameterized import parameterized
from rest_framework import status

from apps.commons.test import JwtAPITestCase, TestRoles
from apps.misc.factories import WikipediaTagFactory
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory
from apps.projects.models import Project


class RetrieveStatsTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization_1 = OrganizationFactory()
        cls.organization_2 = OrganizationFactory()
        cls.project_1 = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[cls.organization_1],
            sdgs=[1, 2],
        )
        cls.project_2 = ProjectFactory(
            publication_status=Project.PublicationStatus.PRIVATE,
            organizations=[cls.organization_1],
            sdgs=[2],
        )
        cls.project_3 = ProjectFactory(
            publication_status=Project.PublicationStatus.ORG,
            organizations=[cls.organization_1, cls.organization_2],
            sdgs=[3],
        )
        cls.project_4 = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[cls.organization_2],
            sdgs=[2],
        )
        cls.date_1 = make_aware(datetime.datetime(2020, 1, 1))
        cls.date_2 = make_aware(datetime.datetime(2020, 2, 1))
        cls.date_3 = make_aware(datetime.datetime(2020, 3, 1))
        Project.objects.filter(pk=cls.project_1.pk).update(
            created_at=cls.date_1, updated_at=cls.date_1
        )
        Project.objects.filter(pk=cls.project_2.pk).update(
            created_at=cls.date_1, updated_at=cls.date_3
        )
        Project.objects.filter(pk=cls.project_3.pk).update(
            created_at=cls.date_2, updated_at=cls.date_3
        )
        Project.objects.filter(pk=cls.project_4.pk).update(
            created_at=cls.date_3, updated_at=cls.date_3
        )
        cls.tag_1 = WikipediaTagFactory()
        cls.tag_2 = WikipediaTagFactory()
        cls.tag_3 = WikipediaTagFactory()
        cls.project_1.wikipedia_tags.add(cls.tag_1)
        cls.project_2.wikipedia_tags.add(cls.tag_1, cls.tag_2)
        cls.project_3.wikipedia_tags.add(cls.tag_3)
        cls.project_4.wikipedia_tags.add(cls.tag_1)

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_ADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_FACILITATOR, status.HTTP_200_OK),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_retrieve_stats(self, role, expected_code):
        user = self.get_parameterized_test_user(role, instances=[self.organization_1])
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("Stats-list", args=(self.organization_1.code,))
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_200_OK:
            content = response.json()
            total = content["total"]
            by_month = content["by_month"]
            by_month_1 = [m for m in by_month if m["month"] == str(self.date_1.date())]
            by_month_2 = [m for m in by_month if m["month"] == str(self.date_2.date())]
            by_month_3 = [m for m in by_month if m["month"] == str(self.date_3.date())]
            by_sdg = [s for s in content["by_sdg"] if s["project_count"] > 0]
            by_sdg_1 = [s for s in by_sdg if s["sdg"] == 1]
            by_sdg_2 = [s for s in by_sdg if s["sdg"] == 2]
            by_sdg_3 = [s for s in by_sdg if s["sdg"] == 3]

            self.assertEqual(total, 4)
            self.assertEqual(len(by_month), 3)
            self.assertEqual(by_month_1[0]["created_count"], 2)
            self.assertEqual(by_month_1[0]["updated_count"], 1)
            self.assertEqual(by_month_2[0]["created_count"], 1)
            self.assertEqual(by_month_2[0]["updated_count"], 0)
            self.assertEqual(by_month_3[0]["created_count"], 0)
            self.assertEqual(by_month_3[0]["updated_count"], 2)

            self.assertEqual(len(by_sdg), 3)
            self.assertEqual(by_sdg_1[0]["project_count"], 1)
            self.assertEqual(by_sdg_2[0]["project_count"], 2)
            self.assertEqual(by_sdg_3[0]["project_count"], 1)

            self.assertEqual(len(content["top_tags"]), 3)
            self.assertEqual(content["top_tags"][0]["id"], self.tag_1.pk)
            self.assertEqual(content["top_tags"][0]["project_count"], 2)
            self.assertIn(content["top_tags"][1]["id"], [self.tag_2.pk, self.tag_3.pk])
            self.assertEqual(content["top_tags"][1]["project_count"], 1)
            self.assertIn(content["top_tags"][2]["id"], [self.tag_2.pk, self.tag_3.pk])
            self.assertEqual(content["top_tags"][2]["project_count"], 1)
