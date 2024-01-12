from unittest.mock import patch

from django.core import mail
from django.urls import reverse
from rest_framework import status

from apps.accounts.factories import PeopleGroupFactory, UserFactory
from apps.feedbacks.factories import FollowFactory
from apps.notifications.models import Notification
from apps.notifications.tasks import _notify_group_as_member_added, _notify_member_added
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory
from apps.projects.models import Project
from apps.projects.tests.views.test_project import ProjectJwtAPITestCase


class AddedMemberTestCase(ProjectJwtAPITestCase):
    @patch("apps.projects.views.notify_member_added.delay")
    def test_notification_task_called(self, notification_task):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        owner = UserFactory()
        project.owners.add(owner)
        self.client.force_authenticate(owner)

        member = UserFactory()
        payload = {Project.DefaultGroup.MEMBERS: [member.keycloak_id]}
        response = self.client.post(
            reverse("Project-add-member", args=(project.id,)), data=payload
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        notification_task.assert_called_once_with(
            project.pk,
            member.pk,
            owner.pk,
            Project.DefaultGroup.MEMBERS,
        )

    @patch("apps.projects.views.notify_group_as_member_added.delay")
    def test_group_notification_task_called(self, notification_task):
        org = OrganizationFactory()
        project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC, organizations=[org]
        )
        owner = UserFactory(groups=[project.get_owners()])
        project.owners.add(owner)
        self.client.force_authenticate(owner)

        group = PeopleGroupFactory(organization=org)
        payload = {
            "people_groups": [group.id],
        }
        response = self.client.post(
            reverse("Project-add-member", args=(project.id,)), data=payload
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        notification_task.assert_called_once_with(
            project.pk,
            group.id,
            owner.pk,
        )

    def test_user_notification_task(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
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
        assert notifications.count() == 3

        for user in [not_notified, notified]:
            notification = notifications.get(receiver=user)
            assert notification.type == Notification.Types.MEMBER_ADDED
            assert notification.project == project
            assert notification.to_send == (user != not_notified)
            assert not notification.is_viewed
            assert notification.count == 1
            new_members = notification.context["new_members"]
            assert {m["id"] for m in new_members} == {member.id}
            assert (
                notification.reminder_message_fr
                == f"{sender.get_full_name()} a ajouté un membre."
            )
            assert (
                notification.reminder_message_en
                == f"{sender.get_full_name()} added a new member."
            )

        notification = notifications.get(receiver=member)
        assert notification.type == Notification.Types.MEMBER_ADDED_SELF
        assert notification.project == project
        assert not notification.to_send
        assert not notification.is_viewed
        assert notification.count == 1

        assert len(mail.outbox) == 1
        assert member.email == mail.outbox[0].to[0]

    def test_group_notification_task(self):
        org = OrganizationFactory()
        project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC, organizations=[org]
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

        group = PeopleGroupFactory(organization=org)
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
        )
        notifications = Notification.objects.filter(project=project)
        assert notifications.count() == 5

        for user in [not_notified, notified]:
            notification = notifications.get(receiver=user)
            assert notification.type == Notification.Types.GROUP_MEMBER_ADDED
            assert notification.project == project
            assert notification.to_send == (user != not_notified)
            assert not notification.is_viewed
            assert notification.count == 1
            assert (
                notification.reminder_message_en
                == f"{sender.get_full_name()} added a group as member to the project {project.title}."
            )

        notification = notifications.get(receiver=member)
        assert notification.type == Notification.Types.GROUP_MEMBER_ADDED_SELF
        assert notification.project == project
        assert not notification.to_send
        assert not notification.is_viewed
        assert notification.count == 1

        emails_outbox = [
            mail.outbox[0].to[0],
            mail.outbox[1].to[0],
            mail.outbox[2].to[0],
        ].sort()
        emails_members = [member.email, leader.email, manager.email].sort()
        assert len(mail.outbox) == 3
        assert emails_members == emails_outbox

    def test_merged_notifications_task(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
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
        assert notifications.count() == 6

        for user in [not_notified, notified]:
            notification = notifications.get(
                receiver=user, type=Notification.Types.MEMBER_ADDED
            )
            assert notification.project == project
            assert notification.to_send == (user != not_notified)
            assert not notification.is_viewed
            assert notification.count == 2
            new_members = notification.context["new_members"]
            assert {m["id"] for m in new_members} == {member_1.id, member_2.id}
            assert (
                notification.reminder_message_fr
                == f"{sender.get_full_name()} a ajouté 2 membres."
            )
            assert (
                notification.reminder_message_en
                == f"{sender.get_full_name()} added 2 new members."
            )

        for user in [member_1, member_2]:
            notification = notifications.get(
                receiver=user, type=Notification.Types.MEMBER_ADDED_SELF
            )
            assert notification.project == project
            assert not notification.to_send
            assert not notification.is_viewed
            assert notification.count == 1
            assert notification.reminder_message_fr == ""
            assert notification.reminder_message_en == ""

        notification = notifications.get(
            receiver=member_1, type=Notification.Types.MEMBER_ADDED
        )
        assert notification.project == project
        assert notification.to_send
        assert not notification.is_viewed
        assert notification.count == 1
        new_members = notification.context["new_members"]
        assert {m["id"] for m in new_members} == {member_2.id}
        assert (
            notification.reminder_message_fr
            == f"{sender.get_full_name()} a ajouté un membre."
        )
        assert (
            notification.reminder_message_en
            == f"{sender.get_full_name()} added a new member."
        )

        assert len(mail.outbox) == 2
        assert {member_1.email, member_2.email} == {
            mail.outbox[0].to[0],
            mail.outbox[1].to[0],
        }
