from django.urls import reverse
from rest_framework import status

from apps.accounts.factories import PeopleGroupFactory, UserFactory
from apps.accounts.models import PeopleGroup
from apps.commons.test import JwtAPITestCase
from apps.organizations.factories import OrganizationFactory


class UnaccentSearchTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()

    def test_user_unaccent_search(self):
        user = UserFactory(
            given_name="ééé", family_name="aaa", email="aaa@aaa.aaa", job="aaa"
        )
        UserFactory(given_name="abc", family_name="abc", email="abc@abc.abc", job="abc")
        for query in ["ééé", "èèè", "êêê", "ëëë", "eee"]:
            response = self.client.get(
                reverse("ProjectUser-list") + f"?search={query}",
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            content = response.json()["results"]
            self.assertEqual(len(content), 1)
            self.assertEqual(content[0]["id"], user.id)

    def test_people_group_unaccent_search(self):
        people_group = PeopleGroupFactory(
            name="ééé",
            publication_status=PeopleGroup.PublicationStatus.PUBLIC,
            organization=self.organization,
        )
        PeopleGroupFactory(
            name="abc",
            publication_status=PeopleGroup.PublicationStatus.PUBLIC,
            organization=self.organization,
        )
        for query in ["ééé", "èèè", "êêê", "ëëë", "eee"]:
            response = self.client.get(
                reverse("PeopleGroup-list", args=(self.organization.code,))
                + f"?search={query}",
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            content = response.json()["results"]
            self.assertEqual(len(content), 1)
            self.assertEqual(content[0]["id"], people_group.id)
