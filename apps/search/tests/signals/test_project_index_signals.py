from django.core.management import call_command
from django.test import override_settings
from django.urls import reverse
from faker import Faker
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase, skipUnlessSearch
from apps.organizations.factories import OrganizationFactory, ProjectCategoryFactory
from apps.projects.factories import ProjectFactory
from apps.skills.factories import TagFactory

faker = Faker()


@skipUnlessSearch
@override_settings(OPENSEARCH_DSL_AUTO_REFRESH=True, OPENSEARCH_DSL_AUTOSYNC=True)
class ProjectIndexUpdateSignalTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.superadmin = UserFactory(groups=[get_superadmins_group()])
        call_command("opensearch", "index", "rebuild", "--force")

    def _search_projects(self, query: str):
        response = self.client.get(
            reverse("Search-search", args=(query,)) + "?types=project"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return response.json()["results"]

    def test_signal_called_on_project_create(self):
        self.client.force_authenticate(self.superadmin)
        payload = {
            "title": faker.sentence(),
            "description": faker.text(),
            "is_locked": faker.boolean(),
            "is_shareable": faker.boolean(),
            "purpose": faker.sentence(),
            "organizations_codes": [self.organization.code],
            "images_ids": [],
        }
        response = self.client.post(reverse("Project-list"), data=payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        post_content = response.json()
        search_content = self._search_projects(payload["title"])
        self.assertIn(
            post_content["id"], [result["project"]["id"] for result in search_content]
        )

    def test_signal_called_on_project_update(self):
        self.client.force_authenticate(self.superadmin)
        project = ProjectFactory(organizations=[self.organization])
        payload = {"title": faker.sentence()}
        response = self.client.patch(
            reverse("Project-detail", args=(project.id,)), payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        search_content = self._search_projects(payload["title"])
        self.assertIn(
            project.id, [result["project"]["id"] for result in search_content]
        )

    def test_signal_called_on_change_members(self):
        self.client.force_authenticate(self.superadmin)
        project = ProjectFactory(organizations=[self.organization])
        user = UserFactory()
        owner = UserFactory()
        project.owners.add(owner)

        # Add member and check if the search index is updated
        payload = {"members": [user.id]}
        response = self.client.post(
            reverse("Project-add-member", args=(project.id,)), payload
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        search_content = self._search_projects(user.given_name)
        self.assertIn(
            project.id, [result["project"]["id"] for result in search_content]
        )

        # Remove member and check if the search index is updated
        payload = {"users": [user.id]}
        response = self.client.post(
            reverse("Project-remove-member", args=(project.id,)), payload
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        search_content = self._search_projects(user.given_name)
        self.assertNotIn(
            project.id, [result["project"]["id"] for result in search_content]
        )

    def test_signal_called_on_change_categories(self):
        self.client.force_authenticate(self.superadmin)
        project = ProjectFactory(organizations=[self.organization])

        # Add category and check if the search index is updated
        category = ProjectCategoryFactory()
        payload = {"project_categories_ids": [category.id]}
        response = self.client.patch(
            reverse("Project-detail", args=(project.id,)), payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        search_content = self._search_projects(category.name)
        self.assertIn(
            project.id, [result["project"]["id"] for result in search_content]
        )

        # Update category and check if the search index is updated
        payload = {"name": faker.word()}
        response = self.client.patch(
            reverse("Category-detail", args=(category.id,)), payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        search_content = self._search_projects(payload["name"])
        self.assertIn(
            project.id, [result["project"]["id"] for result in search_content]
        )

    def test_signal_called_on_change_tags(self):
        self.client.force_authenticate(self.superadmin)
        project = ProjectFactory(organizations=[self.organization])

        # Add tag and check if the search index is updated
        tag = TagFactory(organization=self.organization)
        payload = {"tags": [tag.id]}
        response = self.client.patch(
            reverse("Project-detail", args=(project.id,)), payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        search_content = self._search_projects(tag.title)
        self.assertIn(
            project.id, [result["project"]["id"] for result in search_content]
        )

        # Update tag and check if the search index is updated
        title = faker.word()
        payload = {"title": title, "title_en": title, "title_fr": title}
        response = self.client.patch(
            reverse("OrganizationTag-detail", args=(self.organization.code, tag.id)),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        search_content = self._search_projects(title)
        self.assertIn(
            project.id, [result["project"]["id"] for result in search_content]
        )
