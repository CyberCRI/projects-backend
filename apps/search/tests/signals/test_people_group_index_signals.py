from django.core.management import call_command
from django.test import override_settings
from django.urls import reverse
from faker import Faker
from rest_framework import status

from apps.accounts.factories import PeopleGroupFactory, UserFactory
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase, skipUnlessSearch
from apps.organizations.factories import OrganizationFactory

faker = Faker()


@skipUnlessSearch
@override_settings(OPENSEARCH_DSL_AUTO_REFRESH=True, OPENSEARCH_DSL_AUTOSYNC=True)
class PeopleGroupIndexUpdateSignalTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.superadmin = UserFactory(groups=[get_superadmins_group()])
        call_command("opensearch", "index", "rebuild", "--force")

    def _search_people_groups(self, query: str):
        response = self.client.get(
            reverse("Search-search", args=(query,)) + "?types=people_group"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return response.json()["results"]

    def test_signal_called_on_people_group_create(self):
        self.client.force_authenticate(self.superadmin)
        payload = {
            "name": faker.name(),
            "description": faker.text(),
            "email": faker.email(),
        }
        response = self.client.post(
            reverse("PeopleGroup-list", args=(self.organization.code,)), payload
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        post_content = response.json()
        search_content = self._search_people_groups(payload["name"])
        self.assertIn(
            post_content["id"],
            [result["people_group"]["id"] for result in search_content],
        )

    def test_signal_called_on_people_group_update(self):
        self.client.force_authenticate(self.superadmin)
        people_group = PeopleGroupFactory(organization=self.organization)
        payload = {"name": faker.name()}
        response = self.client.patch(
            reverse(
                "PeopleGroup-detail", args=(self.organization.code, people_group.id)
            ),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        search_content = self._search_people_groups(payload["name"])
        self.assertIn(
            people_group.id, [result["people_group"]["id"] for result in search_content]
        )

    def test_signal_called_on_members_changed(self):
        self.client.force_authenticate(self.superadmin)
        people_group = PeopleGroupFactory(organization=self.organization)
        user = UserFactory()

        # Add member and check if the search index is updated
        payload = {"members": [user.id]}
        response = self.client.post(
            reverse(
                "PeopleGroup-add-member", args=(self.organization.code, people_group.id)
            ),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        search_content = self._search_people_groups(user.given_name)
        self.assertIn(
            people_group.id, [result["people_group"]["id"] for result in search_content]
        )

        # Remove member and check if the search index is updated
        payload = {
            "users": [user.id],
        }
        response = self.client.post(
            reverse(
                "PeopleGroup-remove-member",
                args=(self.organization.code, people_group.id),
            ),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        search_content = self._search_people_groups(user.given_name)
        self.assertNotIn(
            people_group.id, [result["people_group"]["id"] for result in search_content]
        )
