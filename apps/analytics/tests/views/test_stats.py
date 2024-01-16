import datetime
from unittest import skip

from django.urls import reverse
from django.utils.timezone import make_aware
from parameterized import parameterized
from rest_framework import status

from apps.commons.test import JwtAPITestCase, TestRoles
from apps.misc.factories import WikipediaTagFactory
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory
from apps.projects.models import Project


@skip("This view makes no sense and I doubt anyone uses it.")
class RetrieveStatsTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization_1 = OrganizationFactory()
        cls.organization_2 = OrganizationFactory()
        cls.organization_3 = OrganizationFactory()
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

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_403_FORBIDDEN),
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
        response = self.client.get(reverse("Stats-list"))
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_200_OK:
            content = response.json()
            if role == TestRoles.SUPERADMIN:
                by_organization = content["by_organization"]
                assert len(by_organization) == 3
                assert {o["id"] for o in by_organization} == {
                    self.organization_1.pk,
                    self.organization_2.pk,
                    self.organization_3.pk,
                }
                assert [
                    o["project_count"]
                    for o in by_organization
                    if o["id"] == self.organization_1.id
                ][0] == 3
                assert [
                    o["project_count"]
                    for o in by_organization
                    if o["id"] == self.organization_2.id
                ][0] == 2
                by_month = content["by_month"]
                assert len(by_month) == 3
                assert [
                    m["created_count"]
                    for m in by_month
                    if m["month"] == str(self.date_1.date())
                ][0] == 2
                assert [
                    m["updated_count"]
                    for m in by_month
                    if m["month"] == str(self.date_1.date())
                ][0] == 1
                assert [
                    m["created_count"]
                    for m in by_month
                    if m["month"] == str(self.date_2.date())
                ][0] == 1
                assert [
                    m["updated_count"]
                    for m in by_month
                    if m["month"] == str(self.date_2.date())
                ][0] == 0
                assert [
                    m["created_count"]
                    for m in by_month
                    if m["month"] == str(self.date_3.date())
                ][0] == 1
                assert [
                    m["updated_count"]
                    for m in by_month
                    if m["month"] == str(self.date_3.date())
                ][0] == 3
                by_sdg = content["by_sdg"]
                assert [s["project_count"] for s in by_sdg if s["sdg"] == 1][0] == 1
                assert [s["project_count"] for s in by_sdg if s["sdg"] == 2][0] == 3
                assert [s["project_count"] for s in by_sdg if s["sdg"] == 3][0] == 1
                assert len(content["top_tags"]) == 3
                assert content["top_tags"][0]["id"] == self.tag_1.pk
                assert content["top_tags"][0]["project_count"] == 2
                assert content["top_tags"][1]["id"] in [self.tag_2.pk, self.tag_3.pk]
                assert content["top_tags"][1]["project_count"] == 1
                assert content["top_tags"][2]["id"] in [self.tag_2.pk, self.tag_3.pk]
                assert content["top_tags"][2]["project_count"] == 1
            else:
                by_organization = content["by_organization"]
                assert len(by_organization) == 1
                assert by_organization[0]["id"] == self.organization_1.pk
                assert by_organization[0]["project_count"] == 3
                by_month = content["by_month"]
                assert len(by_month) == 3
                assert [
                    m["created_count"]
                    for m in by_month
                    if m["month"] == str(self.date_1.date())
                ][0] == 2
                assert [
                    m["updated_count"]
                    for m in by_month
                    if m["month"] == str(self.date_1.date())
                ][0] == 1
                assert [
                    m["created_count"]
                    for m in by_month
                    if m["month"] == str(self.date_2.date())
                ][0] == 1
                assert [
                    m["updated_count"]
                    for m in by_month
                    if m["month"] == str(self.date_2.date())
                ][0] == 0
                assert [
                    m["created_count"]
                    for m in by_month
                    if m["month"] == str(self.date_3.date())
                ][0] == 0
                assert [
                    m["updated_count"]
                    for m in by_month
                    if m["month"] == str(self.date_3.date())
                ][0] == 2
                by_sdg = content["by_sdg"]
                assert [s["project_count"] for s in by_sdg if s["sdg"] == 1][0] == 1
                assert [s["project_count"] for s in by_sdg if s["sdg"] == 2][0] == 2
                assert [s["project_count"] for s in by_sdg if s["sdg"] == 3][0] == 1
                assert len(content["top_tags"]) == 2
                assert content["top_tags"][0]["id"] == self.tag_1.pk
                assert content["top_tags"][0]["project_count"] == 2
                assert content["top_tags"][1]["id"] == self.tag_2.pk
                assert content["top_tags"][1]["project_count"] == 1
