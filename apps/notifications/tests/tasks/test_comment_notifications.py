from unittest.mock import patch

from django.core import mail
from django.urls import reverse
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.commons.test.testcases import JwtAPITestCase
from apps.feedbacks.factories import CommentFactory, FollowFactory
from apps.notifications.models import Notification
from apps.notifications.tasks import _notify_new_comment
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory
from apps.projects.models import Project


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
        payload = {
            "project_id": project.id,
            "content": "content",
        }
        response = self.client.post(
            reverse("Comment-list", kwargs={"project_id": project.id}), data=payload
        )

        assert response.status_code == status.HTTP_201_CREATED
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
        assert notifications.count() == 3

        for user in [not_notified, notified, follower]:
            notification = notifications.get(receiver=user)
            assert notification.type == Notification.Types.COMMENT
            assert notification.project == project
            assert notification.to_send == (user == follower)
            assert not notification.is_viewed
            assert notification.count == 1
            assert (
                notification.reminder_message_fr
                == f"{sender.get_full_name()} a commenté le projet {project.title}."
            )
            assert (
                notification.reminder_message_en
                == f"{sender.get_full_name()} commented project {project.title}."
            )

        assert len(mail.outbox) == 1
        assert notified.email == mail.outbox[0].to[0]

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
        assert notifications.count() == 3

        for user in [not_notified, notified, follower]:
            notification = notifications.get(receiver=user)
            assert notification.type == Notification.Types.COMMENT
            assert notification.project == project
            assert notification.to_send == (user == follower)
            assert not notification.is_viewed
            assert notification.count == 2
            assert (
                notification.reminder_message_fr
                == f"{sender.get_full_name()} a ajouté 2 commentaires au projet {project.title}."
            )
            assert (
                notification.reminder_message_en
                == f"{sender.get_full_name()} added 2 comments to project {project.title}."
            )
        assert len(mail.outbox) == 2
        assert notified.email == mail.outbox[0].to[0]
        assert notified.email == mail.outbox[1].to[0]


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
            "content": "content",
            "reply_on_id": comment.id,
        }
        response = self.client.post(
            reverse("Comment-list", kwargs={"project_id": project.id}), data=payload
        )

        assert response.status_code == status.HTTP_201_CREATED
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
        assert notifications.count() == 3

        for user in [not_notified, follower]:
            notification = notifications.get(receiver=user)
            assert notification.type == Notification.Types.COMMENT
            assert notification.project == project
            assert notification.receiver == user
            assert notification.to_send == (user == follower)
            assert not notification.is_viewed
            assert notification.count == 1
            assert (
                notification.reminder_message_fr
                == f"{sender.get_full_name()} a commenté le projet {project.title}."
            )
            assert (
                notification.reminder_message_en
                == f"{sender.get_full_name()} commented project {project.title}."
            )

        notification = notifications.get(receiver=notified)
        assert notification.type == Notification.Types.REPLY
        assert notification.project == project
        assert notification.receiver == notified
        assert not notification.to_send
        assert not notification.is_viewed
        assert notification.count == 1
        assert notification.reminder_message_fr == ""
        assert notification.reminder_message_en == ""

        assert len(mail.outbox) == 1
        assert notified.email == mail.outbox[0].to[0]

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
        assert notifications.count() == 3

        for user in [not_notified, follower]:
            notification = notifications.get(receiver=user)
            assert notification.type == Notification.Types.COMMENT
            assert notification.project == project
            assert notification.receiver == user
            assert notification.to_send == (user == follower)
            assert not notification.is_viewed
            assert notification.count == 2
            assert (
                notification.reminder_message_fr
                == f"{sender.get_full_name()} a ajouté 2 commentaires au projet {project.title}."
            )
            assert (
                notification.reminder_message_en
                == f"{sender.get_full_name()} added 2 comments to project {project.title}."
            )

        notification = notifications.get(receiver=notified)
        assert notification.type == Notification.Types.REPLY
        assert notification.project == project
        assert notification.receiver == notified
        assert not notification.to_send
        assert not notification.is_viewed
        assert notification.count == 2
        assert notification.reminder_message_fr == ""
        assert notification.reminder_message_en == ""

        assert len(mail.outbox) == 2
        assert notified.email == mail.outbox[0].to[0]
        assert notified.email == mail.outbox[1].to[0]
