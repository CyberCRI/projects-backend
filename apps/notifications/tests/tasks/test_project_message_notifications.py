from unittest.mock import patch

from django.core import mail
from django.urls import reverse
from faker import Faker
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.commons.test import JwtAPITestCase
from apps.feedbacks.factories import FollowFactory
from apps.notifications.models import Notification
from apps.notifications.tasks import _notify_new_private_message
from apps.organizations.factories import (
    CategoryFollowFactory,
    OrganizationFactory,
    ProjectCategoryFactory,
)
from apps.projects.factories import ProjectFactory, ProjectMessageFactory
from apps.projects.models import Project

faker = Faker()


class NewProjectMessageTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.parent_category = ProjectCategoryFactory(organization=cls.organization)
        cls.category = ProjectCategoryFactory(
            organization=cls.organization, parent=cls.parent_category
        )
        cls.child_category = ProjectCategoryFactory(
            organization=cls.organization, parent=cls.category
        )

    @patch("apps.projects.views.notify_new_private_message.delay")
    def test_notification_task_called(self, notification_task):
        project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[self.organization],
            categories=[self.category],
        )
        owner = UserFactory()
        project.owners.add(owner)

        self.client.force_authenticate(owner)
        payload = {
            "content": faker.text(),
        }
        response = self.client.post(
            reverse("ProjectMessage-list", args=(project.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        message_pk = response.json()["id"]
        notification_task.assert_called_once_with(message_pk)

    def test_notification_task(self):
        project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[self.organization],
            categories=[self.category],
        )
        sender = UserFactory()
        notified = UserFactory()
        not_notified = UserFactory()
        follower = UserFactory()
        category_follower = UserFactory()
        parent_category_follower = UserFactory()
        child_category_follower = UserFactory()
        FollowFactory(follower=follower, project=project)
        CategoryFollowFactory(follower=category_follower, category=self.category)
        CategoryFollowFactory(
            follower=parent_category_follower, category=self.parent_category
        )
        CategoryFollowFactory(
            follower=child_category_follower, category=self.child_category
        )
        project.owners.set([sender, notified, not_notified])

        # Disabling notification for 'not_notified'
        not_notified.notification_settings.project_has_new_private_message = False
        not_notified.notification_settings.save()

        message = ProjectMessageFactory(project=project, author=sender)
        _notify_new_private_message(message.pk)

        notifications = Notification.objects.filter(project=project)
        self.assertEqual(notifications.count(), 2)

        for user in [not_notified, notified]:
            notification = notifications.get(receiver=user)
            self.assertEqual(notification.type, Notification.Types.PROJECT_MESSAGE)
            self.assertEqual(notification.project, project)
            self.assertEqual(notification.to_send, (user == follower))
            self.assertFalse(notification.is_viewed)
            self.assertEqual(notification.count, 1)
            self.assertEqual(
                notification.reminder_message_fr,
                f"{sender.get_full_name()} a envoyé un message au projet {project.title}.",
            )
            self.assertEqual(
                notification.reminder_message_en,
                f"{sender.get_full_name()} posted a message on {project.title}.",
            )

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(notified.email, mail.outbox[0].to[0])

    def test_merged_notifications_task(self):
        project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[self.organization],
            categories=[self.category],
        )
        sender = UserFactory()
        notified = UserFactory()
        not_notified = UserFactory()
        follower = UserFactory()
        category_follower = UserFactory()
        parent_category_follower = UserFactory()
        child_category_follower = UserFactory()
        FollowFactory(follower=follower, project=project)
        CategoryFollowFactory(follower=category_follower, category=self.category)
        CategoryFollowFactory(
            follower=parent_category_follower, category=self.parent_category
        )
        CategoryFollowFactory(
            follower=child_category_follower, category=self.child_category
        )
        project.owners.set([sender, notified, not_notified])

        # Disabling notification for 'not_notified'
        not_notified.notification_settings.project_has_new_private_message = False
        not_notified.notification_settings.save()

        messages = ProjectMessageFactory.create_batch(2, project=project, author=sender)
        _notify_new_private_message(messages[0].pk)
        _notify_new_private_message(messages[1].pk)

        notifications = Notification.objects.filter(project=project)
        self.assertEqual(notifications.count(), 2)

        for user in [not_notified, notified]:
            notification = notifications.get(receiver=user)
            self.assertEqual(notification.type, Notification.Types.PROJECT_MESSAGE)
            self.assertEqual(notification.project, project)
            self.assertEqual(notification.to_send, (user == follower))
            self.assertFalse(notification.is_viewed)
            self.assertEqual(notification.count, 2)
            self.assertEqual(
                notification.reminder_message_fr,
                f"{sender.get_full_name()} a envoyé 2 messages au projet {project.title}.",
            )
            self.assertEqual(
                notification.reminder_message_en,
                f"{sender.get_full_name()} posted 2 messages on project {project.title}.",
            )
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(notified.email, mail.outbox[0].to[0])
        self.assertEqual(notified.email, mail.outbox[1].to[0])
