from unittest.mock import patch

from django.core import mail
from django.urls import reverse
from rest_framework import status

from apps.accounts.factories import PeopleGroupFactory, UserFactory
from apps.commons.test import JwtAPITestCase
from apps.feedbacks.factories import FollowFactory
from apps.notifications.models import Notification
from apps.notifications.tasks import _notify_group_as_member_added, _notify_member_added
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory
from apps.projects.models import Project


class AddedMemberTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()

    @patch("apps.projects.views.notify_member_added.delay")
    def test_notification_task_called(self, notification_task):
        project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[self.organization],
        )
        owner = UserFactory()
        project.owners.add(owner)
        self.client.force_authenticate(owner)

        member = UserFactory()
        payload = {Project.DefaultGroup.MEMBERS: [member.id]}
        response = self.client.post(
            reverse("Project-add-member", args=(project.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        notification_task.assert_called_once_with(
            project.pk,
            member.pk,
            owner.pk,
            Project.DefaultGroup.MEMBERS,
        )

    @patch("apps.projects.views.notify_group_as_member_added.delay")
    def test_group_notification_task_called(self, notification_task):
        project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[self.organization],
        )
        owner = UserFactory(groups=[project.get_owners()])
        project.owners.add(owner)
        self.client.force_authenticate(owner)

        group = PeopleGroupFactory(organization=self.organization)
        payload = {Project.DefaultGroup.MEMBER_GROUPS: [group.id]}
        response = self.client.post(
            reverse("Project-add-member", args=(project.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        notification_task.assert_called_once_with(
            project.pk,
            group.id,
            owner.pk,
            Project.DefaultGroup.MEMBER_GROUPS,
        )

    def test_user_notification_task(self):
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
        project.owners.add(member)
        _notify_member_added(
            project.pk,
            member.pk,
            sender.pk,
            Project.DefaultGroup.MEMBERS,
        )

        notifications = Notification.objects.filter(project=project)
        self.assertEqual(notifications.count(), 3)

        for user in [not_notified, notified]:
            notification = notifications.get(receiver=user)
            self.assertEqual(notification.type, Notification.Types.MEMBER_ADDED)
            self.assertEqual(notification.project, project)
            self.assertEqual(notification.to_send, user != not_notified)
            self.assertFalse(notification.is_viewed)
            self.assertEqual(notification.count, 1)
            new_members = notification.context["new_members"]
            self.assertSetEqual({m["id"] for m in new_members}, {member.id})
            self.assertEqual(
                notification.reminder_message_fr,
                f"{sender.get_full_name()} a ajouté un membre.",
            )
            self.assertEqual(
                notification.reminder_message_en,
                f"{sender.get_full_name()} added a new member.",
            )

        notification = notifications.get(receiver=member)
        self.assertEqual(notification.type, Notification.Types.MEMBER_ADDED_SELF)
        self.assertEqual(notification.project, project)
        self.assertFalse(notification.to_send)
        self.assertFalse(notification.is_viewed)
        self.assertEqual(notification.count, 1)

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(member.email, mail.outbox[0].to[0])

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

        _notify_group_as_member_added(
            project.pk,
            group.id,
            sender.pk,
            "member_groups",
        )
        notifications = Notification.objects.filter(project=project)
        self.assertEqual(notifications.count(), 5)

        for user in [not_notified, notified]:
            notification = notifications.get(receiver=user)
            self.assertEqual(notification.type, Notification.Types.GROUP_MEMBER_ADDED)
            self.assertEqual(notification.project, project)
            self.assertEqual(notification.to_send, user != not_notified)
            self.assertFalse(notification.is_viewed)
            self.assertEqual(notification.count, 1)
            self.assertEqual(
                notification.reminder_message_en,
                f"{sender.get_full_name()} added a group as member to the project {project.title}.",
            )

        notification = notifications.get(receiver=member)
        self.assertEqual(notification.type, Notification.Types.GROUP_MEMBER_ADDED_SELF)
        self.assertEqual(notification.project, project)
        self.assertFalse(notification.to_send)
        self.assertFalse(notification.is_viewed)
        self.assertEqual(notification.count, 1)

        emails_outbox = [
            mail.outbox[0].to[0],
            mail.outbox[1].to[0],
            mail.outbox[2].to[0],
        ].sort()
        emails_members = [member.email, leader.email, manager.email].sort()
        self.assertEqual(len(mail.outbox), 3)
        self.assertEqual(emails_members, emails_outbox)

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
        project.owners.add(member_1)
        project.owners.add(member_2)
        _notify_member_added(
            project.pk, member_1.pk, sender.pk, Project.DefaultGroup.MEMBERS
        )
        project.owners.add(member_2)
        _notify_member_added(
            project.pk,
            member_2.pk,
            sender.pk,
            Project.DefaultGroup.MEMBERS,
        )

        notifications = Notification.objects.filter(project=project)
        self.assertEqual(notifications.count(), 6)

        for user in [not_notified, notified]:
            notification = notifications.get(
                receiver=user, type=Notification.Types.MEMBER_ADDED
            )
            self.assertEqual(notification.project, project)
            self.assertEqual(notification.to_send, user != not_notified)
            self.assertFalse(notification.is_viewed)
            self.assertEqual(notification.count, 2)
            new_members = notification.context["new_members"]
            self.assertSetEqual(
                {m["id"] for m in new_members}, {member_1.id, member_2.id}
            )
            self.assertEqual(
                notification.reminder_message_fr,
                f"{sender.get_full_name()} a ajouté 2 membres.",
            )
            self.assertEqual(
                notification.reminder_message_en,
                f"{sender.get_full_name()} added 2 new members.",
            )

        for user in [member_1, member_2]:
            notification = notifications.get(
                receiver=user, type=Notification.Types.MEMBER_ADDED_SELF
            )
            self.assertEqual(notification.project, project)
            self.assertFalse(notification.to_send)
            self.assertFalse(notification.is_viewed)
            self.assertEqual(notification.count, 1)
            self.assertEqual(notification.reminder_message_fr, "")
            self.assertEqual(notification.reminder_message_en, "")

        notification = notifications.get(
            receiver=member_1, type=Notification.Types.MEMBER_ADDED
        )
        self.assertEqual(notification.project, project)
        self.assertTrue(notification.to_send)
        self.assertFalse(notification.is_viewed)
        self.assertEqual(notification.count, 1)
        new_members = notification.context["new_members"]
        self.assertSetEqual({m["id"] for m in new_members}, {member_2.id})
        self.assertEqual(
            notification.reminder_message_fr,
            f"{sender.get_full_name()} a ajouté un membre.",
        )
        self.assertEqual(
            notification.reminder_message_en,
            f"{sender.get_full_name()} added a new member.",
        )

        self.assertEqual(len(mail.outbox), 2)
        self.assertSetEqual(
            {member_1.email, member_2.email},
            {mail.outbox[0].to[0], mail.outbox[1].to[0]},
        )
