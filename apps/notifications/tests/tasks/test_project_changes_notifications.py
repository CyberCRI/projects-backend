from unittest.mock import patch

from django.urls import reverse
from faker import Faker
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.commons.models import Language
from apps.commons.test import JwtAPITestCase
from apps.feedbacks.factories import FollowFactory
from apps.notifications.models import Notification
from apps.notifications.tasks import _notify_new_blogentry, _notify_project_changes
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import BlogEntryFactory, ProjectFactory
from apps.projects.models import Project

faker = Faker()


class ProjectChangesTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()

    @patch("apps.projects.serializers.notify_project_changes.delay")
    def test_notification_task_called(self, notification_task):
        project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[self.organization],
        )
        owner = UserFactory()
        project.owners.add(owner)
        self.client.force_authenticate(owner)
        payload = {"title": faker.sentence()}
        response = self.client.patch(
            reverse("Project-detail", args=(project.id,)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        notification_task.assert_called_once_with(
            project.pk, {"title": (project.title, payload["title"])}, owner.pk
        )

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
        not_notified.language = Language.FR
        not_notified.save()
        not_notified.notification_settings.project_has_been_edited = False
        not_notified.notification_settings.save()

        _notify_project_changes(
            project.pk,
            {"title": (project.title, faker.sentence())},
            sender.pk,
        )

        notifications = Notification.objects.filter(project=project)
        self.assertEqual(notifications.count(), 3)

        for user in [not_notified, notified, follower]:
            notification = notifications.get(receiver=user)
            self.assertEqual(notification.type, Notification.Types.PROJECT_UPDATED)
            self.assertEqual(notification.project, project)
            self.assertEqual(notification.to_send, user != not_notified)
            self.assertFalse(notification.is_viewed)
            self.assertEqual(notification.count, 1)
            updated_fields = notification.context["updated_fields"]
            self.assertEqual(updated_fields, ["title"])
            self.assertEqual(
                notification.reminder_message_fr,
                f"{sender.get_full_name()} a modifié les champs suivants: titre.",
            )
            self.assertEqual(
                notification.reminder_message_en,
                f"{sender.get_full_name()} edited the title.",
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
        not_notified.language = Language.FR
        not_notified.save()
        not_notified.notification_settings.project_has_been_edited = False
        not_notified.notification_settings.save()

        _notify_project_changes(
            project.pk,
            {"title": (project.title, faker.sentence())},
            sender.pk,
        )
        _notify_project_changes(
            project.pk,
            {"purpose": (project.purpose, faker.sentence())},
            sender.pk,
        )

        notifications = Notification.objects.filter(project=project)
        self.assertEqual(notifications.count(), 3)

        for user in [not_notified, notified, follower]:
            notification = notifications.get(receiver=user)
            self.assertEqual(notification.type, Notification.Types.PROJECT_UPDATED)
            self.assertEqual(notification.project, project)
            self.assertEqual(notification.to_send, user != not_notified)
            self.assertFalse(notification.is_viewed)
            self.assertEqual(notification.count, 2)
            updated_fields = notification.context["updated_fields"]
            self.assertEqual(set(updated_fields), {"main goal", "title"})
            self.assertIn(
                notification.reminder_message_fr,
                [
                    f"{sender.get_full_name()} a modifié les champs suivants: objectif principal et titre.",
                    f"{sender.get_full_name()} a modifié les champs suivants: titre et objectif principal.",
                ],
            )
            self.assertIn(
                notification.reminder_message_en,
                [
                    f"{sender.get_full_name()} edited the main goal and title.",
                    f"{sender.get_full_name()} edited the title and main goal.",
                ],
            )


class NewBlogEntryTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()

    @patch("apps.projects.views.notify_new_blogentry.delay")
    def test_notification_task_called(self, notification_task):
        project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[self.organization],
        )
        owner = UserFactory()
        project.owners.add(owner)
        self.client.force_authenticate(owner)
        payload = {
            "title": faker.sentence(),
            "content": faker.text(),
            "project_id": project.id,
        }
        response = self.client.post(
            reverse("BlogEntry-list", args=(project.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        notification_task.assert_called_once_with(response.data["id"], owner.pk)

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
        not_notified.language = Language.FR
        not_notified.save()
        not_notified.notification_settings.project_has_been_edited = False
        not_notified.notification_settings.save()

        blog_entry = BlogEntryFactory(project=project)
        _notify_new_blogentry(blog_entry.pk, sender.pk)

        notifications = Notification.objects.filter(project=project)
        self.assertEqual(notifications.count(), 3)

        for user in [not_notified, notified, follower]:
            notification = notifications.get(receiver=user)
            self.assertEqual(notification.type, Notification.Types.BLOG_ENTRY)
            self.assertEqual(notification.project, project)
            self.assertEqual(notification.to_send, user != not_notified)
            self.assertFalse(notification.is_viewed)
            self.assertEqual(notification.count, 1)
            self.assertEqual(
                notification.reminder_message_fr,
                f"{sender.get_full_name()} a publié une nouvelle entrée de blog.",
            )
            self.assertEqual(
                notification.reminder_message_en,
                f"{sender.get_full_name()} published a new blog entry.",
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
        not_notified.language = Language.FR
        not_notified.save()
        not_notified.notification_settings.project_has_been_edited = False
        not_notified.notification_settings.save()

        blog_entry_1 = BlogEntryFactory(project=project)
        blog_entry_2 = BlogEntryFactory(project=project)
        _notify_new_blogentry(blog_entry_1.pk, sender.pk)
        _notify_new_blogentry(blog_entry_2.pk, sender.pk)

        notifications = Notification.objects.filter(project=project)
        self.assertEqual(notifications.count(), 3)

        for user in [not_notified, notified, follower]:
            notification = notifications.get(receiver=user)
            self.assertEqual(notification.type, Notification.Types.BLOG_ENTRY)
            self.assertEqual(notification.project, project)
            self.assertEqual(notification.to_send, user != not_notified)
            self.assertFalse(notification.is_viewed)
            self.assertEqual(notification.count, 2)
            self.assertEqual(
                notification.reminder_message_fr,
                f"{sender.get_full_name()} a publié 2 nouvelles entrées de blog.",
            )
            self.assertEqual(
                notification.reminder_message_en,
                f"{sender.get_full_name()} published 2 new blog entries.",
            )
