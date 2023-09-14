from django.urls import reverse
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.announcements.factories import AnnouncementFactory
from apps.commons.test import JwtAPITestCase
from apps.projects.factories import ProjectFactory
from apps.projects.models import Project


class TestParams:
    @staticmethod
    def create_payload(project, user, announcement):
        return {
            "project_id": project.id,
            "announcement_id": announcement.id,
            "applicant_name": user.family_name,
            "applicant_firstname": user.given_name,
            "applicant_email": user.email,
            "applicant_message": "I search a job !",
            "recaptcha": "dummy value",
        }

    def create_data_for_request(self, status, authenticated=False):
        user = UserFactory(
            given_name="given_name", family_name="family_name", email="email@email.fr"
        )
        if authenticated:
            self.client.force_authenticate(user)
        publication_status = {
            "PUBLIC": Project.PublicationStatus.PUBLIC,
            "ORG": Project.PublicationStatus.ORG,
            "PRIVATE": Project.PublicationStatus.PRIVATE,
        }
        project = ProjectFactory(publication_status=publication_status[status])
        project.members.add(user)
        announcement = AnnouncementFactory(project=project)

        payload = self.create_payload(project, user, announcement)
        return {"project_id": project.id, "id": announcement.id}, payload


class AnnouncementApplyTestCaseAnonymous(JwtAPITestCase, TestParams):
    def test_apply_public_anonymous(self):
        kwargs, payload = self.create_data_for_request("PUBLIC")
        response = self.client.post(
            reverse("Announcement-apply", kwargs=kwargs), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_apply_private_anonymous(self):
        kwargs, payload = self.create_data_for_request("PRIVATE")
        response = self.client.post(
            reverse("Announcement-apply", kwargs=kwargs), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_apply_org_anonymous(self):
        kwargs, payload = self.create_data_for_request("ORG")
        response = self.client.post(
            reverse("Announcement-apply", kwargs=kwargs), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class AnnouncementApplyTestCaseAuthenticated(JwtAPITestCase, TestParams):
    def test_apply_public_user(self):
        kwargs, payload = self.create_data_for_request("PUBLIC", authenticated=True)
        response = self.client.post(
            reverse("Announcement-apply", kwargs=kwargs), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_apply_private_user(self):
        kwargs, payload = self.create_data_for_request("PRIVATE", authenticated=True)
        response = self.client.post(
            reverse("Announcement-apply", kwargs=kwargs), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_apply_org_user(self):
        kwargs, payload = self.create_data_for_request("ORG", authenticated=True)
        response = self.client.post(
            reverse("Announcement-apply", kwargs=kwargs), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
