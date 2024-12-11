from unittest.mock import patch

from django.urls import reverse
from faker import Faker
from parameterized import parameterized
from rest_framework import status

from apps.commons.test import JwtAPITestCase, TestRoles
from apps.organizations.factories import OrganizationFactory

faker = Faker()


class ReportTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS,),
            (TestRoles.DEFAULT,),
        ]
    )
    @patch("apps.notifications.views.send_email_task.delay")
    def test_bug_report(self, role, send_email):
        user = self.get_parameterized_test_user(role, instances=[])
        self.client.force_authenticate(user)
        payload = {
            "title": faker.sentence(),
            "message": faker.text(),
            "reported_by": faker.email(),
            "url": faker.url(),
        }
        response = self.client.post(
            reverse("Report-bug", args=(self.organization.code,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        send_email.assert_called_once()

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS,),
            (TestRoles.DEFAULT,),
        ]
    )
    @patch("apps.notifications.views.send_email_task.delay")
    def test_abuse_report(self, role, send_email):
        user = self.get_parameterized_test_user(role, instances=[])
        self.client.force_authenticate(user)
        payload = {
            "title": faker.sentence(),
            "message": faker.text(),
            "reported_by": faker.email(),
            "url": faker.url(),
        }
        response = self.client.post(
            reverse("Report-abuse", args=(self.organization.code,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        send_email.assert_called_once()
