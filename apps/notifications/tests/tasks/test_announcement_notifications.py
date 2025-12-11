from unittest.mock import patch

from django.core import mail
from django.urls import reverse
from faker import Faker
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.announcements.factories import AnnouncementFactory
from apps.announcements.models import Announcement
from apps.commons.test import JwtAPITestCase
from apps.feedbacks.factories import FollowFactory
from apps.notifications.models import Notification
from apps.notifications.tasks import _notify_new_announcement, _notify_new_application
from apps.organizations.factories import (
    CategoryFollowFactory,
    OrganizationFactory,
    ProjectCategoryFactory,
)
from apps.projects.factories import ProjectFactory
from apps.projects.models import Project

faker = Faker()


class NewAnnouncementTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.category = ProjectCategoryFactory(organization=cls.organization)

    @patch("apps.announcements.views.notify_new_announcement.delay")
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
            "title": faker.sentence(),
            "description": faker.text(),
            "type": Announcement.AnnouncementType.JOB,
            "is_remunerated": faker.boolean(),
            "project_id": project.id,
        }
        response = self.client.post(
            reverse("Announcement-list", args=(project.id,)),
            data=payload,
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        announcement_pk = response.json()["id"]
        notification_task.assert_called_once_with(announcement_pk, owner.pk)

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
        FollowFactory(follower=follower, project=project)
        CategoryFollowFactory(follower=category_follower, category=self.category)
        project.owners.set([sender, notified, not_notified])

        # Disabling notification for 'not_notified'
        not_notified.notification_settings.project_has_been_edited = False
        not_notified.notification_settings.save()

        announcement = AnnouncementFactory(project=project)
        _notify_new_announcement(announcement.pk, sender.pk)

        notifications = Notification.objects.filter(project=project)
        self.assertEqual(notifications.count(), 4)

        for user in [not_notified, notified, follower, category_follower]:
            notification = notifications.get(receiver=user)
            self.assertEqual(notification.type, Notification.Types.ANNOUNCEMENT)
            self.assertEqual(notification.project, project)
            self.assertEqual(notification.to_send, user != not_notified)
            self.assertFalse(notification.is_viewed)
            self.assertEqual(notification.count, 1)
            self.assertEqual(
                notification.reminder_message_fr,
                f"{sender.get_full_name()} a publié une nouvelle annonce.",
            )
            self.assertEqual(
                notification.reminder_message_en,
                f"{sender.get_full_name()} published a new announcement.",
            )

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
        FollowFactory(follower=follower, project=project)
        CategoryFollowFactory(follower=category_follower, category=self.category)
        project.owners.set([sender, notified, not_notified])

        # Disabling notification for 'not_notified'
        not_notified.notification_settings.project_has_been_edited = False
        not_notified.notification_settings.save()

        announcement = AnnouncementFactory.create_batch(2, project=project)
        _notify_new_announcement(announcement[0].pk, sender.pk)
        _notify_new_announcement(announcement[1].pk, sender.pk)

        notifications = Notification.objects.filter(project=project)
        self.assertEqual(notifications.count(), 4)

        for user in [not_notified, notified, follower, category_follower]:
            notification = notifications.get(receiver=user)
            self.assertEqual(notification.type, Notification.Types.ANNOUNCEMENT)
            self.assertEqual(notification.project, project)
            self.assertEqual(notification.to_send, user != not_notified)
            self.assertFalse(notification.is_viewed)
            self.assertEqual(notification.count, 2)
            self.assertEqual(
                notification.reminder_message_fr,
                f"{sender.get_full_name()} a publié 2 nouvelles annonces.",
            )
            self.assertEqual(
                notification.reminder_message_en,
                f"{sender.get_full_name()} published 2 new announcements.",
            )


class NewApplicationTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.category = ProjectCategoryFactory(organization=cls.organization)

    @patch("apps.announcements.views.notify_new_application.delay")
    def test_notification_task_called(self, notification_task):
        project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[self.organization],
            categories=[self.category],
        )
        announcement = AnnouncementFactory(project=project)
        application = {
            "applicant_name": faker.last_name(),
            "applicant_firstname": faker.first_name(),
            "applicant_email": faker.email(),
            "applicant_message": faker.text(),
            "recaptcha": faker.word(),
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
            categories=[self.category],
        )
        notified = UserFactory()
        not_notified = UserFactory()
        follower = UserFactory()
        category_follower = UserFactory()
        FollowFactory(follower=follower, project=project)
        CategoryFollowFactory(follower=category_follower, category=self.category)
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
        self.assertEqual(notifications.count(), 2)

        for user in [not_notified, notified]:
            notification = notifications.get(receiver=user)
            self.assertEqual(notification.type, Notification.Types.APPLICATION)
            self.assertEqual(notification.project, project)
            self.assertEqual(notification.receiver, user)
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
            categories=[self.category],
        )
        notified = UserFactory()
        not_notified = UserFactory()
        follower = UserFactory()
        category_follower = UserFactory()
        FollowFactory(follower=follower, project=project)
        CategoryFollowFactory(follower=category_follower, category=self.category)
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
        self.assertEqual(notifications.count(), 4)  # merge is set to False
