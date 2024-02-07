from unittest.mock import patch

from django.core import mail
from django.urls import reverse
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.announcements.factories import AnnouncementFactory
from apps.announcements.models import Announcement
from apps.commons.test.testcases import JwtAPITestCase
from apps.feedbacks.factories import FollowFactory
from apps.notifications.models import Notification
from apps.notifications.tasks import _notify_new_announcement, _notify_new_application
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory
from apps.projects.models import Project


class NewAnnouncementTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()

    @patch("apps.announcements.views.notify_new_announcement.delay")
    def test_notification_task_called(self, notification_task):
        project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[self.organization],
        )
        owner = UserFactory()

        project.owners.add(owner)
        self.client.force_authenticate(owner)
        payload = {
            "title": "title",
            "description": "description",
            "type": Announcement.AnnouncementType.JOB,
            "is_remunerated": True,
            "project_id": project.id,
        }
        response = self.client.post(
            reverse("Announcement-list", args=(project.id,)),
            data=payload,
        )

        assert response.status_code == status.HTTP_201_CREATED
        announcement_pk = response.json()["id"]
        notification_task.assert_called_once_with(announcement_pk, owner.pk)

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
        not_notified.notification_settings.project_has_been_edited = False
        not_notified.notification_settings.save()

        announcement = AnnouncementFactory(project=project)
        _notify_new_announcement(announcement.pk, sender.pk)

        notifications = Notification.objects.filter(project=project)
        assert notifications.count() == 3

        for user in [not_notified, notified, follower]:
            notification = notifications.get(receiver=user)
            assert notification.type == Notification.Types.ANNOUNCEMENT
            assert notification.project == project
            assert notification.to_send == (user != not_notified)
            assert not notification.is_viewed
            assert notification.count == 1
            assert (
                notification.reminder_message_fr
                == f"{sender.get_full_name()} a publié une nouvelle annonce."
            )
            assert (
                notification.reminder_message_en
                == f"{sender.get_full_name()} published a new announcement."
            )

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
        not_notified.notification_settings.project_has_been_edited = False
        not_notified.notification_settings.save()

        announcement = AnnouncementFactory.create_batch(2, project=project)
        _notify_new_announcement(announcement[0].pk, sender.pk)
        _notify_new_announcement(announcement[1].pk, sender.pk)

        notifications = Notification.objects.filter(project=project)
        assert notifications.count() == 3

        for user in [not_notified, notified, follower]:
            notification = notifications.get(receiver=user)
            assert notification.type == Notification.Types.ANNOUNCEMENT
            assert notification.project == project
            assert notification.to_send == (user != not_notified)
            assert not notification.is_viewed
            assert notification.count == 2
            assert (
                notification.reminder_message_fr
                == f"{sender.get_full_name()} a publié 2 nouvelles annonces."
            )
            assert (
                notification.reminder_message_en
                == f"{sender.get_full_name()} published 2 new announcements."
            )


class NewApplicationTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()

    @patch("apps.announcements.views.notify_new_application.delay")
    def test_notification_task_called(self, notification_task):
        project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[self.organization],
        )
        announcement = AnnouncementFactory(project=project)
        application = {
            "applicant_name": "name",
            "applicant_firstname": "firstname",
            "applicant_email": "email@email.com",
            "applicant_message": "message",
            "recaptcha": "captcha",
        }
        payload = {
            "project_id": project.id,
            "announcement_id": announcement.id,
            **application,
        }
        self.client.post(
            reverse("Announcement-apply", args=(project.id, announcement.id)),
            data=payload,
        )
        notification_task.assert_called_once_with(announcement.pk, application)

    def test_notification_task(self):
        project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[self.organization],
        )
        notified = UserFactory()
        not_notified = UserFactory()
        follower = UserFactory()
        FollowFactory(follower=follower, project=project)
        project.owners.set([notified, not_notified])

        # Disabling notification for 'not_notified'
        not_notified.notification_settings.announcement_has_new_application = False
        not_notified.notification_settings.save()

        announcement = AnnouncementFactory(project=project)
        _notify_new_application(
            announcement.pk,
            {
                "applicant_name": "name",
                "applicant_firstname": "firstname",
                "applicant_email": "email@email.com",
                "applicant_message": "message",
                "recaptcha": "captcha",
                "project_id": project.id,
                "announcement_id": announcement.id,
            },
        )

        notifications = Notification.objects.filter(project=project)
        assert notifications.count() == 2

        for user in [not_notified, notified]:
            notification = notifications.get(receiver=user)
            assert notification.type == Notification.Types.APPLICATION
            assert notification.project == project
            assert notification.receiver == user
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
        notified = UserFactory()
        not_notified = UserFactory()
        follower = UserFactory()
        FollowFactory(follower=follower, project=project)
        project.owners.set([notified, not_notified])

        # Disabling notification for 'not_notified'
        not_notified.notification_settings.announcement_has_new_application = False
        not_notified.notification_settings.save()

        announcement = AnnouncementFactory(project=project)
        _notify_new_application(
            announcement.pk,
            {
                "applicant_name": "name",
                "applicant_firstname": "firstname",
                "applicant_email": "email@email.com",
                "applicant_message": "message",
                "recaptcha": "captcha",
                "project_id": project.id,
                "announcement_id": announcement.id,
            },
        )
        _notify_new_application(
            announcement.pk,
            {
                "applicant_name": "name",
                "applicant_firstname": "firstname",
                "applicant_email": "email@email.com",
                "applicant_message": "message",
                "recaptcha": "captcha",
                "project_id": project.id,
                "announcement_id": announcement.id,
            },
        )

        notifications = Notification.objects.filter(project=project)
        assert notifications.count() == 4  # merge is set to False
