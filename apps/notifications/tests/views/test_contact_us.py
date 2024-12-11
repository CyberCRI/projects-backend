from unittest.mock import patch

from django.urls import reverse
from faker import Faker
from parameterized import parameterized
from rest_framework import status

from apps.commons.test import JwtAPITestCase, TestRoles
from apps.organizations.factories import OrganizationFactory

faker = Faker()


class ContactTestCase(JwtAPITestCase):
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
    def test_contact_us(self, role, send_email):
        user = self.get_parameterized_test_user(role, instances=[])
        self.client.force_authenticate(user)
        payload = {
            "subject": faker.sentence(),
            "content": faker.text(),
            "email": faker.email(),
        }
        response = self.client.post(
            reverse("Contact-us", args=(self.organization.code,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        send_email.assert_called_once()
