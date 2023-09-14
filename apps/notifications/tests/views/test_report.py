from unittest.mock import patch

from django.urls import reverse
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.commons.test import JwtAPITestCase


@patch("apps.notifications.views.send_email_task.delay")
class ReportTestCaseAnonymous(JwtAPITestCase):
    def test_bug_report(self, send_email):
        payload = {
            "title": "Title",
            "message": "This is a bug",
            "reported_by": "test@mail.com",
            "url": "https://www.website.com",
        }
        response = self.client.post(reverse("Report-bug"), data=payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        send_email.assert_called_once()

    def test_abuse_report(self, send_email):
        payload = {
            "title": "Title",
            "message": "This is an abuse",
            "reported_by": "test@mail.com",
            "url": "https://www.website.com",
        }
        response = self.client.post(reverse("Report-abuse"), data=payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        send_email.assert_called_once()


@patch("apps.notifications.views.send_email_task.delay")
class ReportTestCaseUser(JwtAPITestCase):
    def test_bug_report(self, send_email):
        payload = {
            "title": "Title",
            "message": "This is a bug",
            "reported_by": "test@mail.com",
            "url": "https://www.website.com",
        }
        self.client.force_authenticate(UserFactory())
        response = self.client.post(reverse("Report-bug"), data=payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        send_email.assert_called_once()

    def test_abuse_report(self, send_email):
        payload = {
            "title": "Title",
            "message": "This is an abuse",
            "reported_by": "test@mail.com",
            "url": "https://www.website.com",
        }
        self.client.force_authenticate(UserFactory())
        response = self.client.post(reverse("Report-abuse"), data=payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        send_email.assert_called_once()
