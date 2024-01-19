from unittest.mock import patch

from django.core import mail
from django.urls import reverse
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.feedbacks.factories import FollowFactory
from apps.notifications.models import Notification
from apps.notifications.tasks import _notify_member_updated
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory
from apps.projects.models import Project
from apps.projects.tests.views.test_project import ProjectJwtAPITestCase


class UpdatedMemberTestCase(ProjectJwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()

    @patch("apps.projects.views.notify_member_updated.delay")
    def test_notification_task_called(self, notification_task):
        project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[self.organization],
        )
        owner = UserFactory()
        project.owners.add(owner)
        self.client.force_authenticate(owner)

        member = UserFactory()
        project.owners.add(member)
        payload = {
            Project.DefaultGroup.MEMBERS: [member.keycloak_id],
        }
        response = self.client.post(
            reverse("Project-add-member", args=(project.id,)), data=payload
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        notification_task.assert_called_once_with(
            project.pk,
            member.pk,
            owner.pk,
            Project.DefaultGroup.MEMBERS.value,
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
        not_notified.notification_settings.project_has_been_edited = False
        not_notified.notification_settings.save()

        member = UserFactory()
        project.owners.add(member)
        _notify_member_updated(
            project.pk,
            member.pk,
            sender.pk,
            Project.DefaultGroup.MEMBERS,
        )

        notifications = Notification.objects.filter(project=project)
        assert notifications.count() == 3

        for user in [not_notified, notified]:
            notification = notifications.get(receiver=user)
            assert notification.type == Notification.Types.MEMBER_UPDATED
            assert notification.project == project
            assert notification.to_send == (user != not_notified)
            assert not notification.is_viewed
            assert notification.count == 1
            modified_members = notification.context["modified_members"]
            assert {(m["id"], m["role"]) for m in modified_members} == {
                (member.id, "participant")
            }
            assert (
                notification.reminder_message_fr
                == f"{sender.get_full_name()} a mis à jour le rôle d'un membre."
            )
            assert (
                notification.reminder_message_en
                == f"{sender.get_full_name()} updated a member."
            )

        notification = notifications.get(receiver=member)
        assert notification.type == Notification.Types.MEMBER_UPDATED_SELF
        assert notification.project == project
        assert not notification.to_send
        assert not notification.is_viewed
        assert notification.count == 1

        assert len(mail.outbox) == 1
        assert member.email == mail.outbox[0].to[0]

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
        _notify_member_updated(
            project.pk,
            member_1.pk,
            sender.pk,
            Project.DefaultGroup.MEMBERS,
        )
        _notify_member_updated(
            project.pk,
            member_2.pk,
            sender.pk,
            Project.DefaultGroup.REVIEWERS,
        )

        notifications = Notification.objects.filter(project=project)
        assert notifications.count() == 6

        for user in [not_notified, notified]:
            notification = notifications.get(
                receiver=user, type=Notification.Types.MEMBER_UPDATED
            )
            assert notification.project == project
            assert notification.to_send == (user != not_notified)
            assert not notification.is_viewed
            assert notification.count == 2
            modified_members = notification.context["modified_members"]
            assert {(m["id"], m["role"]) for m in modified_members} == {
                (member_1.id, "participant"),
                (member_2.id, "reviewer"),
            }
            assert (
                notification.reminder_message_fr
                == f"{sender.get_full_name()} a mis à jour le rôle de 2 membres."
            )
            assert (
                notification.reminder_message_en
                == f"{sender.get_full_name()} updated 2 members."
            )

        for user in [member_1, member_2]:
            notification = notifications.get(
                receiver=user, type=Notification.Types.MEMBER_UPDATED
            )
            assert notification.project == project
            assert notification.to_send
            assert not notification.is_viewed
            assert notification.count == 1
            modified_members = notification.context["modified_members"]
            if user == member_1:
                assert {(m["id"], m["role"]) for m in modified_members} == {
                    (member_2.id, "reviewer")
                }
            else:
                assert {(m["id"], m["role"]) for m in modified_members} == {
                    (member_1.id, "participant")
                }
            assert (
                notification.reminder_message_fr
                == f"{sender.get_full_name()} a mis à jour le rôle d'un membre."
            )
            assert (
                notification.reminder_message_en
                == f"{sender.get_full_name()} updated a member."
            )

            notification = notifications.get(
                receiver=user, type=Notification.Types.MEMBER_UPDATED_SELF
            )
            assert notification.project == project
            assert not notification.to_send
            assert not notification.is_viewed
            assert notification.count == 1
            modified_members = notification.context["modified_members"]
            assert {(m["id"], m["role"]) for m in modified_members} == {
                (user.id, "reviewer" if user == member_2 else "participant")
            }
            assert notification.reminder_message_fr == ""
            assert notification.reminder_message_en == ""

        assert len(mail.outbox) == 2
        assert {member_1.email, member_2.email} == {
            mail.outbox[0].to[0],
            mail.outbox[1].to[0],
        }
