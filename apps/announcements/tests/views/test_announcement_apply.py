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


class AnnouncementApplyTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.projects = {
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
            "public": AnnouncementFactory(project=cls.projects["public"]),
            "org": AnnouncementFactory(project=cls.projects["org"]),
            "private": AnnouncementFactory(project=cls.projects["private"]),
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
    def test_apply_to_announcement(self, role, publication_status):
        user = self.get_parameterized_test_user(role)
        project = self.projects[publication_status]
        announcement = self.announcements[publication_status]
        if user:
            self.client.force_authenticate(user)
        payload = {
            "project_id": project.id,
            "announcement_id": announcement.id,
            "applicant_name": faker.last_name(),
            "applicant_firstname": faker.first_name(),
            "applicant_email": faker.email(),
            "applicant_message": faker.text(),
            "recaptcha": faker.word(),
        }
        response = self.client.post(
            reverse("Announcement-apply", args=(project.id, announcement.id)),
            data=payload,
        )
        assert response.status_code == status.HTTP_200_OK
