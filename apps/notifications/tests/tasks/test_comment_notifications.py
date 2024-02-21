from unittest.mock import patch

from django.core import mail
from django.urls import reverse
from faker import Faker
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.commons.test.testcases import JwtAPITestCase
from apps.feedbacks.factories import CommentFactory, FollowFactory
from apps.notifications.models import Notification
from apps.notifications.tasks import _notify_new_comment
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory
from apps.projects.models import Project

faker = Faker()


class NewCommentTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()

    @patch("apps.feedbacks.views.notify_new_comment.delay")
    def test_notification_task_called(self, notification_task):
        project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[self.organization],
        )
        owner = UserFactory()
        project.owners.add(owner)

        self.client.force_authenticate(owner)
        payload = {"project_id": project.id, "content": faker.text()}
        response = self.client.post(
            reverse("Comment-list", args=(project.id,)), data=payload
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        comment_pk = response.json()["id"]
        notification_task.assert_called_once_with(comment_pk)

    def test_notification_task(self):
        project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[self.organization],
        )
        sender = UserFactory()
        notified = UserFactory()
        not_notified = UserFactory()
        follower = UserFactory()
        FollowFactory(follower=follower, project=project)
        project.owners.set([sender, notified, not_notified])

        # Disabling notification for 'not_notified'
        not_notified.notification_settings.project_has_been_commented = False
        not_notified.notification_settings.save()

        comment = CommentFactory(project=project, author=sender)
        _notify_new_comment(comment.pk)

        notifications = Notification.objects.filter(project=project)
        self.assertEqual(notifications.count(), 3)

        for user in [not_notified, notified, follower]:
            notification = notifications.get(receiver=user)
            self.assertEqual(notification.type, Notification.Types.COMMENT)
            self.assertEqual(notification.project, project)
            self.assertEqual(notification.to_send, (user == follower))
            self.assertFalse(notification.is_viewed)
            self.assertEqual(notification.count, 1)
            self.assertEqual(
                notification.reminder_message_fr,
                f"{sender.get_full_name()} a commenté le projet {project.title}.",
            )
            self.assertEqual(
                notification.reminder_message_en,
                f"{sender.get_full_name()} commented project {project.title}.",
            )

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(notified.email, mail.outbox[0].to[0])

    def test_merged_notifications_task(self):
        project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[self.organization],
        )
        sender = UserFactory()
        notified = UserFactory()
        not_notified = UserFactory()
        follower = UserFactory()
        FollowFactory(follower=follower, project=project)
        project.owners.set([sender, notified, not_notified])

        # Disabling notification for 'not_notified'
        not_notified.notification_settings.project_has_been_commented = False
        not_notified.notification_settings.save()

        comments = CommentFactory.create_batch(2, project=project, author=sender)
        _notify_new_comment(comments[0].pk)
        _notify_new_comment(comments[1].pk)

        notifications = Notification.objects.filter(project=project)
        self.assertEqual(notifications.count(), 3)

        for user in [not_notified, notified, follower]:
            notification = notifications.get(receiver=user)
            self.assertEqual(notification.type, Notification.Types.COMMENT)
            self.assertEqual(notification.project, project)
            self.assertEqual(notification.to_send, (user == follower))
            self.assertFalse(notification.is_viewed)
            self.assertEqual(notification.count, 2)
            self.assertEqual(
                notification.reminder_message_fr,
                f"{sender.get_full_name()} a ajouté 2 commentaires au projet {project.title}.",
            )
            self.assertEqual(
                notification.reminder_message_en,
                f"{sender.get_full_name()} added 2 comments to project {project.title}.",
            )
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(notified.email, mail.outbox[0].to[0])
        self.assertEqual(notified.email, mail.outbox[1].to[0])


class NewReplyTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()

    @patch("apps.feedbacks.views.notify_new_comment.delay")
    def test_notification_task_called(self, notification_task):
        project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[self.organization],
        )
        comment = CommentFactory(project=project)
        owner = UserFactory()
        project.owners.add(owner)

        self.client.force_authenticate(owner)
        payload = {
            "project_id": project.id,
            "content": faker.text(),
            "reply_on_id": comment.id,
        }
        response = self.client.post(
            reverse("Comment-list", args=(project.id,)), data=payload
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        comment_pk = response.json()["id"]
        notification_task.assert_called_once_with(comment_pk)

    def test_notification_task(self):
        project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[self.organization],
        )
        sender = UserFactory()
        notified = UserFactory()
        not_notified = UserFactory()
        follower = UserFactory()
        FollowFactory(follower=follower, project=project)
        project.owners.set([sender, notified, not_notified])

        # Disabling notification for 'not_notified'
        not_notified.notification_settings.project_has_been_commented = False
        not_notified.notification_settings.save()

        comment = CommentFactory(project=project, author=notified)
        reply = CommentFactory(project=project, reply_on=comment, author=sender)
        _notify_new_comment(reply.pk)

        notifications = Notification.objects.filter(project=project)
        self.assertEqual(notifications.count(), 3)

        for user in [not_notified, follower]:
            notification = notifications.get(receiver=user)
            self.assertEqual(notification.type, Notification.Types.COMMENT)
            self.assertEqual(notification.project, project)
            self.assertEqual(notification.receiver, user)
            self.assertEqual(notification.to_send, (user == follower))
            self.assertFalse(notification.is_viewed)
            self.assertEqual(notification.count, 1)
            self.assertEqual(
                notification.reminder_message_fr,
                f"{sender.get_full_name()} a commenté le projet {project.title}.",
            )
            self.assertEqual(
                notification.reminder_message_en,
                f"{sender.get_full_name()} commented project {project.title}.",
            )

        notification = notifications.get(receiver=notified)
        self.assertEqual(notification.type, Notification.Types.REPLY)
        self.assertEqual(notification.project, project)
        self.assertEqual(notification.receiver, notified)
        self.assertFalse(notification.to_send)
        self.assertFalse(notification.is_viewed)
        self.assertEqual(notification.count, 1)
        self.assertEqual(notification.reminder_message_fr, "")
        self.assertEqual(notification.reminder_message_en, "")

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(notified.email, mail.outbox[0].to[0])

    def test_merged_notifications_task(self):
        project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[self.organization],
        )
        sender = UserFactory()
        notified = UserFactory()
        not_notified = UserFactory()
        follower = UserFactory()
        FollowFactory(follower=follower, project=project)
        project.owners.set([sender, notified, not_notified])

        # Disabling notification for 'not_notified'
        not_notified.notification_settings.project_has_been_commented = False
        not_notified.notification_settings.save()

        comment = CommentFactory(project=project, author=notified)
        reply_1 = CommentFactory(project=project, reply_on=comment, author=sender)
        reply_2 = CommentFactory(project=project, reply_on=comment, author=sender)
        _notify_new_comment(reply_1.pk)
        _notify_new_comment(reply_2.pk)

        notifications = Notification.objects.filter(project=project)
        self.assertEqual(notifications.count(), 3)

        for user in [not_notified, follower]:
            notification = notifications.get(receiver=user)
            self.assertEqual(notification.type, Notification.Types.COMMENT)
            self.assertEqual(notification.project, project)
            self.assertEqual(notification.receiver, user)
            self.assertEqual(notification.to_send, (user == follower))
            self.assertFalse(notification.is_viewed)
            self.assertEqual(notification.count, 2)
            self.assertEqual(
                notification.reminder_message_fr,
                f"{sender.get_full_name()} a ajouté 2 commentaires au projet {project.title}.",
            )
            self.assertEqual(
                notification.reminder_message_en,
                f"{sender.get_full_name()} added 2 comments to project {project.title}.",
            )

        notification = notifications.get(receiver=notified)
        self.assertEqual(notification.type, Notification.Types.REPLY)
        self.assertEqual(notification.project, project)
        self.assertEqual(notification.receiver, notified)
        self.assertFalse(notification.to_send)
        self.assertFalse(notification.is_viewed)
        self.assertEqual(notification.count, 2)
        self.assertEqual(notification.reminder_message_fr, "")
        self.assertEqual(notification.reminder_message_en, "")

        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(notified.email, mail.outbox[0].to[0])
        self.assertEqual(notified.email, mail.outbox[1].to[0])
