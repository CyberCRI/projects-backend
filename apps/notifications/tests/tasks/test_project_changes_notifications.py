from unittest.mock import patch

from django.urls import reverse
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.feedbacks.factories import FollowFactory
from apps.misc.models import Language
from apps.notifications.models import Notification
from apps.notifications.tasks import _notify_new_blogentry, _notify_project_changes
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import BlogEntryFactory, ProjectFactory
from apps.projects.models import Project
from apps.projects.tests.views.test_project import ProjectJwtAPITestCase


class ProjectChangesTestCase(ProjectJwtAPITestCase):
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
        payload = {"title": "title"}
        response = self.client.patch(
            reverse("Project-detail", args=(project.id,)),
            data=payload,
        )
        assert response.status_code == status.HTTP_200_OK
        notification_task.assert_called_once_with(
            project.pk, {"title": (project.title, "title")}, owner.pk
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
            project.pk, {"title": (project.title, "title")}, sender.pk
        )

        notifications = Notification.objects.filter(project=project)
        assert notifications.count() == 3

        for user in [not_notified, notified, follower]:
            notification = notifications.get(receiver=user)
            assert notification.type == Notification.Types.PROJECT_UPDATED
            assert notification.project == project
            assert notification.to_send == (user != not_notified)
            assert not notification.is_viewed
            assert notification.count == 1
            updated_fields = notification.context["updated_fields"]
            assert updated_fields == ["title"]
            assert (
                notification.reminder_message_fr
                == f"{sender.get_full_name()} a modifié les champs suivants: titre."
            )
            assert (
                notification.reminder_message_en
                == f"{sender.get_full_name()} edited the title."
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
            project.pk, {"title": (project.title, "title")}, sender.pk
        )
        _notify_project_changes(
            project.pk, {"purpose": (project.purpose, "purpose")}, sender.pk
        )

        notifications = Notification.objects.filter(project=project)
        assert notifications.count() == 3

        for user in [not_notified, notified, follower]:
            notification = notifications.get(receiver=user)
            assert notification.type == Notification.Types.PROJECT_UPDATED
            assert notification.project == project
            assert notification.to_send == (user != not_notified)
            assert not notification.is_viewed
            assert notification.count == 2
            updated_fields = notification.context["updated_fields"]
            assert set(updated_fields) == {"main goal", "title"}
            assert notification.reminder_message_fr in [
                f"{sender.get_full_name()} a modifié les champs suivants: objectif principal et titre.",
                f"{sender.get_full_name()} a modifié les champs suivants: titre et objectif principal.",
            ]
            assert notification.reminder_message_en in [
                f"{sender.get_full_name()} edited the main goal and title.",
                f"{sender.get_full_name()} edited the title and main goal.",
            ]


class NewBlogEntryTestCase(ProjectJwtAPITestCase):
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
        payload = {"title": "title", "content": "content", "project_id": project.id}
        response = self.client.post(
            reverse("BlogEntry-list", args=(project.id,)), data=payload
        )
        assert response.status_code == status.HTTP_201_CREATED
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
        assert notifications.count() == 3

        for user in [not_notified, notified, follower]:
            notification = notifications.get(receiver=user)
            assert notification.type == Notification.Types.BLOG_ENTRY
            assert notification.project == project
            assert notification.to_send == (user != not_notified)
            assert not notification.is_viewed
            assert notification.count == 1
            assert (
                notification.reminder_message_fr
                == f"{sender.get_full_name()} a publié une nouvelle entrée de blog."
            )
            assert (
                notification.reminder_message_en
                == f"{sender.get_full_name()} published a new blog entry."
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
        assert notifications.count() == 3

        for user in [not_notified, notified, follower]:
            notification = notifications.get(receiver=user)
            assert notification.type == Notification.Types.BLOG_ENTRY
            assert notification.project == project
            assert notification.to_send == (user != not_notified)
            assert not notification.is_viewed
            assert notification.count == 2
            assert (
                notification.reminder_message_fr
                == f"{sender.get_full_name()} a publié 2 nouvelles entrées de blog."
            )
            assert (
                notification.reminder_message_en
                == f"{sender.get_full_name()} published 2 new blog entries."
            )
