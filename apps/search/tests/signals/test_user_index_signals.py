from unittest.mock import patch

from django.core.management import call_command
from django.test import override_settings
from django.urls import reverse
from faker import Faker
from rest_framework import status

from apps.accounts.factories import PeopleGroupFactory, SeedUserFactory, UserFactory
from apps.accounts.models import PeopleGroup
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase, skipUnlessSearch
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory
from apps.projects.models import Project
from apps.skills.factories import TagFactory

faker = Faker()


@skipUnlessSearch
@override_settings(OPENSEARCH_DSL_AUTO_REFRESH=True, OPENSEARCH_DSL_AUTOSYNC=True)
class UserIndexUpdateSignalTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.superadmin = UserFactory(groups=[get_superadmins_group()])
        call_command("opensearch", "index", "rebuild", "--force")

    def _search_users(self, query: str):
        response = self.client.get(
            reverse("Search-search", args=(query,)) + "?types=user"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return response.json()["results"]

    @patch("services.keycloak.interface.KeycloakService.send_email")
    def test_signal_called_on_user_creation(self, email_mock):
        email_mock.return_value = {}
        self.client.force_authenticate(self.superadmin)
        payload = {
            "email": faker.email(),
            "given_name": faker.first_name(),
            "family_name": faker.last_name(),
            "roles_to_add": [self.organization.get_users().name],
        }
        response = self.client.post(
            reverse("ProjectUser-list") + f"?organization={self.organization.code}",
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        post_content = response.json()
        search_content = self._search_users(payload["given_name"])
        self.assertIn(
            post_content["id"], [result["user"]["id"] for result in search_content]
        )

    def test_signal_called_on_user_update(self):
        self.client.force_authenticate(self.superadmin)
        payload = {"given_name": faker.first_name()}
        user = SeedUserFactory()
        response = self.client.patch(
            reverse("ProjectUser-detail", args=(user.id,)), payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        search_content = self._search_users(payload["given_name"])
        self.assertIn(user.id, [result["user"]["id"] for result in search_content])

    def test_signal_called_on_change_roles(self):
        self.client.force_authenticate(self.superadmin)
        project = ProjectFactory(organizations=[self.organization])
        user = SeedUserFactory()

        # Add user to project and check if the search index is updated
        payload = {"roles_to_add": [project.get_members().name]}
        response = self.client.patch(
            reverse("ProjectUser-detail", args=(user.id,)), payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        search_content = self._search_users(project.title)
        self.assertIn(user.id, [result["user"]["id"] for result in search_content])

        # Remove user from project and check if the search index is updated
        payload = {"roles_to_remove": [project.get_members().name]}
        response = self.client.patch(
            reverse("ProjectUser-detail", args=(user.id,)), payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        search_content = self._search_users(project.title)
        self.assertNotIn(user.id, [result["user"]["id"] for result in search_content])

    def test_signal_called_on_change_people_group_role(self):
        self.client.force_authenticate(self.superadmin)
        people_group = PeopleGroupFactory(organization=self.organization)
        user = UserFactory()

        # Add user to people group and check if the search index is updated
        payload = {PeopleGroup.DefaultGroup.MEMBERS: [user.id]}
        response = self.client.post(
            reverse(
                "PeopleGroup-add-member",
                args=(self.organization.code, people_group.id),
            ),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        search_content = self._search_users(people_group.name)
        self.assertIn(user.id, [result["user"]["id"] for result in search_content])

        # Remove user from people group and check if the search index is updated
        payload = {"users": [user.id]}
        response = self.client.post(
            reverse(
                "PeopleGroup-remove-member",
                args=(self.organization.code, people_group.id),
            ),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        search_content = self._search_users(people_group.name)
        self.assertNotIn(user.id, [result["user"]["id"] for result in search_content])

    def test_signal_called_on_change_project_role(self):
        self.client.force_authenticate(self.superadmin)
        project = ProjectFactory(organizations=[self.organization])
        user = UserFactory()
        owner = UserFactory()
        project.owners.add(owner)

        # Add user to project and check if the search index is updated
        payload = {Project.DefaultGroup.MEMBERS: [user.id]}
        response = self.client.post(
            reverse("Project-add-member", args=(project.id,)),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        search_content = self._search_users(project.title)
        self.assertIn(user.id, [result["user"]["id"] for result in search_content])

        # Remove user from project and check if the search index is updated
        payload = {"users": [user.id]}
        response = self.client.post(
            reverse("Project-remove-member", args=(project.id,)),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        search_content = self._search_users(project.title)
        self.assertNotIn(user.id, [result["user"]["id"] for result in search_content])

    def test_signal_called_on_skill_change(self):
        self.client.force_authenticate(self.superadmin)
        user = UserFactory()
        tag = TagFactory(organization=self.organization)

        # Add skill and check if the search index is updated
        payload = {
            "tag": tag.id,
            "level": faker.pyint(1, 4),
            "level_to_reach": faker.pyint(1, 4),
        }
        response = self.client.post(
            reverse("Skill-list", args=(user.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        search_content = self._search_users(tag.title)
        self.assertIn(user.id, [result["user"]["id"] for result in search_content])

        # Update skill and check if the search index is updated
        title = faker.word()
        payload = {"title": title, "title_en": title, "title_fr": title}
        response = self.client.patch(
            reverse("OrganizationTag-detail", args=(self.organization.code, tag.id)),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        search_content = self._search_users(title)
        self.assertIn(user.id, [result["user"]["id"] for result in search_content])
