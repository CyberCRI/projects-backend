from unittest.mock import patch

from django.urls import reverse
from rest_framework import status

from apps.accounts.factories import PeopleGroupFactory, UserFactory
from apps.commons.test.testcases import JwtAPITestCase
from apps.feedbacks.factories import FollowFactory
from apps.notifications.models import Notification
from apps.notifications.tasks import (
    _notify_group_member_deleted,
    _notify_member_deleted,
)
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory
from apps.projects.models import Project


class DeletedMemberTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()

    @patch("apps.projects.views.notify_member_deleted.delay")
    def test_notification_task_called(self, notification_task):
        project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[self.organization],
        )
        owner = UserFactory()
        project.owners.add(owner)
        self.client.force_authenticate(owner)

        member = UserFactory()
        project.members.add(member)
        payload = {
            "users": [member.id],
        }
        response = self.client.post(
            reverse("Project-remove-member", args=(project.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        notification_task.assert_called_once_with(project.pk, member.pk, owner.pk)

    @patch("apps.projects.views.notify_group_member_deleted.delay")
    def test_group_notification_task_called(self, notification_task):
        project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[self.organization],
        )
        owner = UserFactory()
        project.owners.add(owner)
        self.client.force_authenticate(owner)

        group = PeopleGroupFactory(organization=self.organization)
        project.member_people_groups.add(group)
        payload = {
            "people_groups": [group.id],
        }
        response = self.client.post(
            reverse("Project-remove-member", args=(project.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        notification_task.assert_called_once_with(project.pk, group.pk, owner.pk)

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

        member = UserFactory()
        _notify_member_deleted(project.pk, member.pk, sender.pk)

        notifications = Notification.objects.filter(project=project)
        self.assertEqual(notifications.count(), 2)

        for user in [not_notified, notified]:
            notification = notifications.get(receiver=user)
            self.assertEqual(notification.type, Notification.Types.MEMBER_REMOVED)
            self.assertEqual(notification.project, project)
            self.assertEqual(notification.to_send, user != not_notified)
            self.assertFalse(notification.is_viewed)
            self.assertEqual(notification.count, 1)
            deleted_members = notification.context["deleted_members"]
            self.assertSetEqual({m["id"] for m in deleted_members}, {member.id})
            self.assertEqual(
                notification.reminder_message_fr,
                f"{sender.get_full_name()} a retiré un membre.",
            )
            self.assertEqual(
                notification.reminder_message_en,
                f"{sender.get_full_name()} removed a member.",
            )

    def test_group_notification_task(self):
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

        group = PeopleGroupFactory(organization=self.organization)
        leader = UserFactory()
        manager = UserFactory()
        group.leaders.add(leader)
        group.managers.add(manager)
        member = UserFactory()
        group.members.add(member)

        _notify_group_member_deleted(
            project.pk,
            group.pk,
            sender.pk,
        )

        notifications = Notification.objects.filter(project=project)
        self.assertEqual(notifications.count(), 2)

        for user in [not_notified, notified]:
            notification = notifications.get(receiver=user)
            self.assertEqual(notification.type, Notification.Types.GROUP_MEMBER_REMOVED)
            self.assertEqual(notification.project, project)
            self.assertEqual(notification.to_send, user != not_notified)
            self.assertFalse(notification.is_viewed)
            self.assertEqual(notification.count, 1)
            self.assertEqual(
                notification.reminder_message_fr,
                f"{sender.get_full_name()} a retiré un groupe des membres.",
            )
            self.assertEqual(
                notification.reminder_message_en,
                f"{sender.get_full_name()} removed a group from members.",
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

        member_1 = UserFactory()
        member_2 = UserFactory()
        _notify_member_deleted(project.pk, member_1.pk, sender.pk)
        _notify_member_deleted(project.pk, member_2.pk, sender.pk)

        notifications = Notification.objects.filter(project=project)
        self.assertEqual(notifications.count(), 2)

        for user in [not_notified, notified]:
            notification = notifications.get(receiver=user)
            self.assertEqual(notification.type, Notification.Types.MEMBER_REMOVED)
            self.assertEqual(notification.project, project)
            self.assertEqual(notification.to_send, user != not_notified)
            self.assertFalse(notification.is_viewed)
            self.assertEqual(notification.count, 2)
            deleted_members = notification.context["deleted_members"]
            self.assertSetEqual(
                {m["id"] for m in deleted_members}, {member_1.id, member_2.id}
            )
            self.assertEqual(
                notification.reminder_message_fr,
                f"{sender.get_full_name()} a retiré 2 membres.",
            )
            self.assertEqual(
                notification.reminder_message_en,
                f"{sender.get_full_name()} removed 2 members.",
            )
