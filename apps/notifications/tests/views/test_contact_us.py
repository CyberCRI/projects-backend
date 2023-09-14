from unittest.mock import patch

from django.urls import reverse
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.commons.test import JwtAPITestCase


@patch("apps.notifications.views.send_email_task.delay")
class ContactTestCaseAnonymous(JwtAPITestCase):
    def test_contact_us(self, send_email):
        payload = {
            "subject": "Subject",
            "content": "This is a message",
            "email": "test@mail.com",
        }
        response = self.client.post(reverse("Contact-us"), data=payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        send_email.assert_called_once()


@patch("apps.notifications.views.send_email_task.delay")
class ContactTestCaseUser(JwtAPITestCase):
    def test_contact_us(self, send_email):
        payload = {
            "subject": "Subject",
            "content": "This is a message",
            "email": "test@mail.com",
        }
        self.client.force_authenticate(UserFactory())
        response = self.client.post(reverse("Contact-us"), data=payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        send_email.assert_called_once()
