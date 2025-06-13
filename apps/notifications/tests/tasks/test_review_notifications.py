from unittest.mock import patch

from django.core import mail
from django.urls import reverse
from faker import Faker
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.commons.test import JwtAPITestCase
from apps.feedbacks.factories import FollowFactory, ReviewFactory
from apps.notifications.models import Notification
from apps.notifications.tasks import _notify_new_review, _notify_ready_for_review
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory
from apps.projects.models import Project

faker = Faker()


class NewReviewTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()

    @patch("apps.feedbacks.views.notify_new_review.delay")
    def test_notification_task_called(self, notification_task):
        project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[self.organization],
        )
        category = project.categories.first()
        category.is_reviewable = True
        category.save()
        project.life_status = Project.LifeStatus.TO_REVIEW
        project.save()
        reviewer = UserFactory()
        project.reviewers.add(reviewer)

        self.client.force_authenticate(reviewer)
        payload = {
            "project_id": project.id,
            "title": faker.sentence(),
            "description": faker.text(),
        }
        response = self.client.post(
            reverse("Reviewed-list", args=(project.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        review_pk = response.json()["id"]
        notification_task.assert_called_once_with(review_pk)

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
        project.reviewers.add(sender)
        project.owners.set([notified, not_notified])

        # Disabling notification for 'not_notified'
        not_notified.notification_settings.project_has_been_reviewed = False
        not_notified.notification_settings.save()

        review = ReviewFactory(project=project, reviewer=sender)
        _notify_new_review(review.pk)

        notifications = Notification.objects.filter(project=project)
        self.assertEqual(notifications.count(), 3)

        for user in [not_notified, notified, follower]:
            notification = notifications.get(receiver=user)
            self.assertEqual(notification.type, Notification.Types.REVIEW)
            self.assertEqual(notification.project, project)
            self.assertFalse(notification.to_send)
            self.assertFalse(notification.is_viewed)
            self.assertEqual(notification.count, 1)
            self.assertEqual(notification.reminder_message_fr, "")
            self.assertEqual(notification.reminder_message_en, "")
        self.assertEqual(len(mail.outbox), 2)
        self.assertSetEqual(
            {notified.email, follower.email},
            {mail.outbox[0].to[0], mail.outbox[1].to[0]},
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
        project.reviewers.add(sender)
        project.owners.set([notified, not_notified])

        # Disabling notification for 'not_notified'
        not_notified.notification_settings.project_has_been_reviewed = False
        not_notified.notification_settings.save()

        reviews = ReviewFactory.create_batch(2, project=project, reviewer=sender)
        _notify_new_review(reviews[0].pk)
        _notify_new_review(reviews[1].pk)

        notifications = Notification.objects.filter(project=project)
        self.assertEqual(notifications.count(), 3)

        for user in [not_notified, notified, follower]:
            notification = notifications.get(receiver=user)
            self.assertEqual(notification.type, Notification.Types.REVIEW)
            self.assertEqual(notification.project, project)
            self.assertFalse(notification.to_send)
            self.assertFalse(notification.is_viewed)
            self.assertEqual(notification.count, 2)
            self.assertEqual(notification.reminder_message_fr, "")
            self.assertEqual(notification.reminder_message_en, "")

        self.assertEqual(len(mail.outbox), 4)
        self.assertEqual(
            [mail.outbox[i].to[0] for i in range(4)].count(notified.email), 2
        )
        self.assertEqual(
            [mail.outbox[i].to[0] for i in range(4)].count(follower.email), 2
        )


class ReadyForReviewTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()

    @patch("apps.projects.views.notify_ready_for_review.delay")
    def test_notification_task_called(self, notification_task):
        project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[self.organization],
        )
        owner = UserFactory()
        project.owners.add(owner)

        self.client.force_authenticate(owner)
        payload = {"life_status": Project.LifeStatus.TO_REVIEW}
        response = self.client.patch(
            reverse("Project-detail", args=(project.id,)), data=payload
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        notification_task.assert_called_once_with(project.id, owner.id)

    def test_notification_task(self):
        project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[self.organization],
        )
        owners = UserFactory.create_batch(3)
        project.owners.set(owners)
        members = UserFactory.create_batch(3)
        project.members.set(members)
        FollowFactory.create_batch(3, project=project)

        notified = UserFactory()
        not_notified = UserFactory()
        project.reviewers.set([notified, not_notified])

        # Disabling notification for 'not_notified'
        not_notified.notification_settings.project_ready_for_review = False
        not_notified.notification_settings.save()
        _notify_ready_for_review(project.pk, owners[0].pk)

        notifications = Notification.objects.filter(project=project)
        self.assertEqual(notifications.count(), 2)
        for user in [not_notified, notified]:
            notification = notifications.get(receiver=user)
            self.assertEqual(notification.type, Notification.Types.READY_FOR_REVIEW)
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
        )
        owners = UserFactory.create_batch(3)
        project.owners.set(owners)
        members = UserFactory.create_batch(3)
        project.members.set(members)
        FollowFactory.create_batch(3, project=project)

        notified = UserFactory()
        not_notified = UserFactory()
        project.reviewers.set([notified, not_notified])

        # Disabling notification for 'not_notified'
        not_notified.notification_settings.project_ready_for_review = False
        not_notified.notification_settings.save()
        _notify_ready_for_review(project.pk, owners[0].pk)
        _notify_ready_for_review(project.pk, owners[0].pk)

        notifications = Notification.objects.filter(project=project)
        self.assertEqual(notifications.count(), 2)

        for user in [not_notified, notified]:
            notification = notifications.get(receiver=user)
            self.assertEqual(notification.type, Notification.Types.READY_FOR_REVIEW)
            self.assertEqual(notification.project, project)
            self.assertEqual(notification.receiver, user)
            self.assertFalse(notification.to_send)
            self.assertFalse(notification.is_viewed)
            self.assertEqual(notification.count, 2)
            self.assertEqual(notification.reminder_message_fr, "")
            self.assertEqual(notification.reminder_message_en, "")

        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(notified.email, mail.outbox[0].to[0])
        self.assertEqual(notified.email, mail.outbox[1].to[0])
