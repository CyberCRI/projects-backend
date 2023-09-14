from unittest.mock import patch

from django.urls import reverse
from rest_framework import status

from apps.accounts.factories import PeopleGroupFactory, UserFactory
from apps.feedbacks.factories import FollowFactory
from apps.notifications.models import Notification
from apps.notifications.tasks import (
    _notify_group_member_deleted,
    _notify_member_deleted,
)
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory
from apps.projects.models import Project
from apps.projects.tests.views.test_project import ProjectJwtAPITestCase


class DeletedMemberTestCase(ProjectJwtAPITestCase):
    @patch("apps.projects.views.notify_member_deleted.delay")
    def test_notification_task_called(self, notification_task):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        owner = UserFactory()
        project.owners.add(owner)
        self.client.force_authenticate(owner)

        member = UserFactory()
        project.members.add(member)
        payload = {
            "users": [member.keycloak_id],
        }
        response = self.client.post(
            reverse("Project-remove-member", args=(project.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        notification_task.assert_called_once_with(project.pk, member.pk, owner.pk)

    @patch("apps.projects.views.notify_group_member_deleted.delay")
    def test_group_notification_task_called(self, notification_task):
        org = OrganizationFactory()
        project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC, organizations=[org]
        )
        owner = UserFactory()
        project.owners.add(owner)
        self.client.force_authenticate(owner)

        group = PeopleGroupFactory(organization=org)
        project.member_people_groups.add(group)
        payload = {
            "member_people_group": group.id,
        }
        response = self.client.post(
            reverse("Project-remove-member", args=(project.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        notification_task.assert_called_once_with(project.pk, owner.pk)

    def test_notification_task(self):
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
        _notify_member_deleted(project.pk, member.pk, sender.pk)

        notifications = Notification.objects.filter(project=project)
        assert notifications.count() == 2

        for user in [not_notified, notified]:
            notification = notifications.get(receiver=user)
            assert notification.type == Notification.Types.MEMBER_REMOVED
            assert notification.project == project
            assert notification.to_send == (user != not_notified)
            assert not notification.is_viewed
            assert notification.count == 1
            deleted_members = notification.context["deleted_members"]
            assert {m["keycloak_id"] for m in deleted_members} == {member.keycloak_id}
            assert (
                notification.reminder_message_fr
                == f"{sender.get_full_name()} a retiré un membre."
            )
            assert (
                notification.reminder_message_en
                == f"{sender.get_full_name()} removed a member."
            )

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

        _notify_group_member_deleted(
            project.pk,
            sender.pk,
        )

        notifications = Notification.objects.filter(project=project)
        assert notifications.count() == 2

        for user in [not_notified, notified]:
            notification = notifications.get(receiver=user)
            assert notification.type == Notification.Types.GROUP_MEMBER_REMOVED
            assert notification.project == project
            assert notification.to_send == (user != not_notified)
            assert not notification.is_viewed
            assert notification.count == 1
            assert (
                notification.reminder_message_fr
                == f"{sender.get_full_name()} a retiré un groupe des membres."
            )
            assert (
                notification.reminder_message_en
                == f"{sender.get_full_name()} removed a group from members."
            )

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
        _notify_member_deleted(project.pk, member_1.pk, sender.pk)
        _notify_member_deleted(project.pk, member_2.pk, sender.pk)

        notifications = Notification.objects.filter(project=project)
        assert notifications.count() == 2

        for user in [not_notified, notified]:
            notification = notifications.get(receiver=user)
            assert notification.type == Notification.Types.MEMBER_REMOVED
            assert notification.project == project
            assert notification.to_send == (user != not_notified)
            assert not notification.is_viewed
            assert notification.count == 2
            deleted_members = notification.context["deleted_members"]
            assert {m["keycloak_id"] for m in deleted_members} == {
                member_1.keycloak_id,
                member_2.keycloak_id,
            }
            assert (
                notification.reminder_message_fr
                == f"{sender.get_full_name()} a retiré 2 membres."
            )
            assert (
                notification.reminder_message_en
                == f"{sender.get_full_name()} removed 2 members."
            )
