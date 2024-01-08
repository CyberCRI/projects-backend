from django.urls import reverse
from faker import Faker
from parameterized import parameterized
from rest_framework import status

from apps.announcements.factories import AnnouncementFactory
from apps.commons.test import JwtAPITestCase, TestRoles
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory
from apps.projects.models import Project

faker = Faker()


class ReadAnnouncementTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        projects = {
            "public": ProjectFactory(
                organizations=[cls.organization],
                publication_status=Project.PublicationStatus.PUBLIC,
            ),
            "org": ProjectFactory(
                organizations=[cls.organization],
                publication_status=Project.PublicationStatus.ORG,
            ),
            "private": ProjectFactory(
                organizations=[cls.organization],
                publication_status=Project.PublicationStatus.PRIVATE,
            ),
        }
        cls.announcements = {
            "public": AnnouncementFactory(project=projects["public"]),
            "org": AnnouncementFactory(project=projects["org"]),
            "private": AnnouncementFactory(project=projects["private"]),
        }

    @parameterized.expand(
        [
            (
                TestRoles.ANONYMOUS,
                "public",
            ),
            (
                TestRoles.ANONYMOUS,
                "org",
            ),
            (
                TestRoles.ANONYMOUS,
                "private",
            ),
            (
                TestRoles.DEFAULT,
                "public",
            ),
            (
                TestRoles.DEFAULT,
                "org",
            ),
            (
                TestRoles.DEFAULT,
                "private",
            ),
        ]
    )
    def test_retrieve_announcement(self, role, publication_status):
        user = self.get_parameterized_test_user(role)
        announcement = self.announcements[publication_status]
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("Read-announcement-detail", args=(announcement.id,)),
        )
        assert response.status_code == status.HTTP_200_OK
        content = response.json()
        assert content["id"] == announcement.id

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS,),
            (TestRoles.DEFAULT,),
        ]
    )
    def test_list_announcement(self, role):
        user = self.get_parameterized_test_user(role)
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("Read-announcement-list"),
        )
        assert response.status_code == status.HTTP_200_OK
        content = response.json()["results"]
        assert len(content) == 3
        assert {a["id"] for a in content} == {a.id for a in self.announcements.values()}
