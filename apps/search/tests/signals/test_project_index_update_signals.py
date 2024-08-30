from unittest.mock import patch

from django.urls import reverse
from faker import Faker
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase, TagTestCaseMixin
from apps.misc.factories import TagFactory
from apps.organizations.factories import OrganizationFactory, ProjectCategoryFactory
from apps.projects.factories import ProjectFactory
from apps.projects.models import Project

faker = Faker()


class ProjectIndexUpdateSignalTestCase(JwtAPITestCase, TagTestCaseMixin):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.project = ProjectFactory(organizations=[cls.organization], with_owner=True)
        cls.superadmin = UserFactory(groups=[get_superadmins_group()])

    @patch("apps.search.tasks.update_or_create_project_search_object_task.delay")
    def test_signal_called_on_project_creation(self, signal):
        self.client.force_authenticate(self.superadmin)
        payload = {
            "organizations_codes": [self.organization.code],
            "title": faker.sentence(),
            "description": faker.text(),
            "purpose": faker.sentence(),
        }
        response = self.client.post(reverse("Project-list"), payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        content = response.json()
        project = ProjectFactory(id=content["id"])
        signal.assert_called_with(project.pk)

    @patch("apps.search.tasks.update_or_create_project_search_object_task.delay")
    def test_signal_called_on_project_update(self, signal):
        self.client.force_authenticate(self.superadmin)
        payload = {"publication_status": Project.PublicationStatus.PRIVATE}
        response = self.client.patch(
            reverse("Project-detail", args=(self.project.pk,)),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        signal.assert_called_with(self.project.pk)

    @patch("apps.search.tasks.update_or_create_project_search_object_task.delay")
    def test_signal_called_on_new_organization(self, signal):
        self.client.force_authenticate(self.superadmin)
        organization = OrganizationFactory()
        payload = {"organizations_codes": [organization.code, self.organization.code]}
        response = self.client.patch(
            reverse("Project-detail", args=(self.project.pk,)),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        signal.assert_called_with(self.project.pk)

    @patch("apps.search.tasks.update_or_create_project_search_object_task.delay")
    def test_signal_called_on_add_members(self, signal):
        self.client.force_authenticate(self.superadmin)
        user = UserFactory()
        payload = {
            Project.DefaultGroup.MEMBERS: [user.id],
        }
        response = self.client.post(
            reverse("Project-add-member", args=(self.project.id,)),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        signal.assert_called_with(self.project.pk)

    @patch("apps.search.tasks.update_or_create_project_search_object_task.delay")
    def test_signal_called_on_remove_member(self, signal):
        self.client.force_authenticate(self.superadmin)
        user = UserFactory(groups=[self.project.get_members()])
        payload = {
            "users": [user.id],
        }
        response = self.client.post(
            reverse("Project-remove-member", args=(self.project.id,)),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        signal.assert_called_with(self.project.pk)

    @patch("apps.search.tasks.update_or_create_project_search_object_task.delay")
    def test_signal_called_on_update_team(self, signal):
        self.client.force_authenticate(self.superadmin)
        member = UserFactory()
        owner = UserFactory()
        reviewer = UserFactory()
        payload = {
            "team": {
                Project.DefaultGroup.MEMBERS: [member.id],
                Project.DefaultGroup.OWNERS: [owner.id],
                Project.DefaultGroup.REVIEWERS: [reviewer.id],
            }
        }
        response = self.client.patch(
            reverse("Project-detail", args=(self.project.pk,)),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        signal.assert_called_with(self.project.pk)

    @patch("apps.search.tasks.update_or_create_project_search_object_task.delay")
    def test_signal_called_on_new_categories(self, signal):
        self.client.force_authenticate(self.superadmin)
        category = ProjectCategoryFactory(organization=self.organization)
        payload = {"categories_ids": [category.id]}
        response = self.client.patch(
            reverse("Project-detail", args=(self.project.pk,)),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        signal.assert_called_with(self.project.pk)

    @patch("services.wikipedia.interface.WikipediaService.wbgetentities")
    @patch("apps.search.tasks.update_or_create_project_search_object_task.delay")
    def test_signal_called_on_new_wikipedia_tags(self, signal, wikipedia_mock):
        wikipedia_mock.side_effect = self.get_wikipedia_tag_mocked_side_effect
        self.client.force_authenticate(self.superadmin)
        wikipedia_tag = self.get_random_wikipedia_qid()
        payload = {"wikipedia_tags": [wikipedia_tag]}
        response = self.client.patch(
            reverse("Project-detail", args=(self.project.pk,)),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        signal.assert_called_with(self.project.pk)

    @patch("apps.search.tasks.update_or_create_project_search_object_task.delay")
    def test_signal_called_on_new_organization_tags(self, signal):
        self.client.force_authenticate(self.superadmin)
        tag = TagFactory(organization=self.organization)
        payload = {"organizations_tags_ids": [tag.id]}
        response = self.client.patch(
            reverse("Project-detail", args=(self.project.pk,)),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        signal.assert_called_with(self.project.pk)
