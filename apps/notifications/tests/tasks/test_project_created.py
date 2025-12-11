from unittest.mock import patch

from django.urls import reverse
from faker import Faker
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.commons.enums import Language
from apps.commons.test import JwtAPITestCase
from apps.notifications.models import Notification
from apps.notifications.tasks import _notify_new_project
from apps.organizations.factories import (
    CategoryFollowFactory,
    OrganizationFactory,
    ProjectCategoryFactory,
)
from apps.projects.factories import ProjectFactory
from apps.projects.models import Project

faker = Faker()


class ProjectCreatedTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.category = ProjectCategoryFactory(organization=cls.organization)
        cls.sender = UserFactory(groups=[cls.organization.get_admins()])

    @patch("apps.projects.serializers.notify_new_project.delay")
    def test_notification_task_called(self, notification_task):
        self.client.force_authenticate(self.sender)
        payload = {
            "organizations_codes": [self.organization.code],
            "title": faker.sentence(),
            "description": faker.text(),
            "is_shareable": faker.boolean(),
            "purpose": faker.sentence(),
            "project_categories_ids": [self.category.id],
        }
        response = self.client.post(reverse("Project-list"), data=payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        content = response.json()
        notification_task.assert_called_once_with(content["id"], self.sender.pk)

    def test_notification_task(self):
        project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[self.organization],
            categories=[self.category],
        )
        fr_category_follower = UserFactory(language=Language.FR)
        en_category_follower = UserFactory(language=Language.EN)
        not_notified = UserFactory()
        not_notified.notification_settings.category_project_created = False
        not_notified.notification_settings.save()
        CategoryFollowFactory(follower=fr_category_follower, category=self.category)
        CategoryFollowFactory(follower=en_category_follower, category=self.category)
        CategoryFollowFactory(follower=not_notified, category=self.category)
        CategoryFollowFactory(follower=self.sender, category=self.category)

        _notify_new_project(project.pk, self.sender.pk)

        notifications = Notification.objects.filter(project=project)
        self.assertEqual(notifications.count(), 3)

        for user in [fr_category_follower, en_category_follower, not_notified]:
            notification = notifications.get(receiver=user)
            self.assertEqual(notification.type, Notification.Types.PROJECT_CREATED)
            self.assertEqual(notification.project, project)
            self.assertEqual(notification.to_send, user != not_notified)
            self.assertFalse(notification.is_viewed)
            self.assertEqual(notification.count, 1)
            category_pk = notification.context["category_pk"]
            self.assertEqual(category_pk, self.category.pk)
            self.assertEqual(
                notification.reminder_message_fr,
                f"{self.sender.get_full_name()} a créé le projet {project.title} dans la catégorie {self.category.name}.",
            )
            self.assertEqual(
                notification.reminder_message_en,
                f"{self.sender.get_full_name()} created project {project.title} in category {self.category.name}.",
            )
