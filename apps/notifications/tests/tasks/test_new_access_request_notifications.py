from unittest.mock import patch

from django.core import mail
from django.urls import reverse
from faker import Faker
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.commons.test import JwtAPITestCase
from apps.invitations.factories import AccessRequestFactory
from apps.notifications.models import Notification
from apps.notifications.tasks import _notify_new_access_request
from apps.organizations.factories import OrganizationFactory

faker = Faker()


class NewAccessRequestTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()

    @patch("apps.invitations.views.notify_new_access_request.delay")
    def test_notification_task_called(self, notification_task):
        payload = {
            "email": faker.email(),
            "given_name": faker.first_name(),
            "family_name": faker.last_name(),
            "job": faker.sentence(),
            "message": faker.text(),
        }
        response = self.client.post(
            reverse("AccessRequest-list", args=(self.organization.code,)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        access_request_pk = response.json()["id"]
        notification_task.assert_called_once_with(access_request_pk)

    def test_notification_task(self):
        notified = UserFactory()
        not_notified = UserFactory()
        self.organization.admins.set([notified, not_notified])
        # Disabling notification for 'not_notified'
        not_notified.notification_settings.organization_has_new_access_request = False
        not_notified.notification_settings.save()

        access_request = AccessRequestFactory(organization=self.organization)
        _notify_new_access_request(access_request.pk)

        notifications = Notification.objects.filter(organization=self.organization)
        self.assertEqual(notifications.count(), 2)
        for user in [notified, not_notified]:
            notification = notifications.get(receiver=user)
            self.assertEqual(notification.type, Notification.Types.ACCESS_REQUEST)
            self.assertEqual(notification.project, None)
            self.assertEqual(notification.to_send, False)
            self.assertFalse(notification.is_viewed)
            self.assertEqual(notification.count, 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(len(mail.outbox[0].to), 1)
        self.assertEqual(notified.email, mail.outbox[0].to[0])
        self.assertEqual(
            mail.outbox[0].subject,
            f"New access request {access_request.id} for {self.organization.name} Projects platform",
        )

    def test_merged_notifications_task(self):
        notified = UserFactory()
        not_notified = UserFactory()
        self.organization.admins.set([notified, not_notified])
        # Disabling notification for 'not_notified'
        not_notified.notification_settings.organization_has_new_access_request = False
        not_notified.notification_settings.save()

        access_requests = AccessRequestFactory.create_batch(
            2, organization=self.organization
        )
        _notify_new_access_request(access_requests[0].pk)
        _notify_new_access_request(access_requests[1].pk)

        notifications = Notification.objects.filter(organization=self.organization)
        self.assertEqual(notifications.count(), 2)
        for user in [notified, not_notified]:
            notification = notifications.get(receiver=user)
            self.assertEqual(notification.type, Notification.Types.ACCESS_REQUEST)
            self.assertEqual(notification.project, None)
            self.assertEqual(notification.to_send, False)
            self.assertFalse(notification.is_viewed)
            self.assertEqual(notification.count, 2)
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(len(mail.outbox[0].to), 1)
        self.assertEqual(len(mail.outbox[1].to), 1)
        self.assertEqual(notified.email, mail.outbox[0].to[0])
        self.assertEqual(notified.email, mail.outbox[1].to[0])
        self.assertEqual(
            mail.outbox[0].subject,
            f"New access request {access_requests[0].id} for {self.organization.name} Projects platform",
        )
        self.assertEqual(
            mail.outbox[1].subject,
            f"New access request {access_requests[1].id} for {self.organization.name} Projects platform",
        )
