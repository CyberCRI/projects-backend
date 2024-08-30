from unittest.mock import patch

from django.urls import reverse
from faker import Faker
from rest_framework import status

from apps.accounts.factories import PeopleGroupFactory, UserFactory
from apps.accounts.models import PeopleGroup
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase
from apps.organizations.factories import OrganizationFactory

faker = Faker()


class PeopleGroupIndexUpdateSignalTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.people_group = PeopleGroupFactory(organization=cls.organization)
        cls.superadmin = UserFactory(groups=[get_superadmins_group()])

    @patch("apps.search.tasks.update_or_create_people_group_search_object_task.delay")
    def test_signal_called_on_people_group_creation(self, signal):
        self.client.force_authenticate(self.superadmin)
        payload = {
            "name": faker.name(),
            "description": faker.text(),
            "email": faker.email(),
            "parent": self.people_group.pk,
        }
        response = self.client.post(
            reverse("PeopleGroup-list", args=(self.organization.code,)),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        content = response.json()
        people_group = PeopleGroup.objects.get(id=content["id"])
        signal.assert_called_with(people_group.pk)

    @patch("apps.search.tasks.update_or_create_people_group_search_object_task.delay")
    def test_signal_called_on_people_group_update(self, signal):
        self.client.force_authenticate(self.superadmin)
        payload = {"publication_status": PeopleGroup.PublicationStatus.PRIVATE}
        response = self.client.patch(
            reverse(
                "PeopleGroup-detail",
                args=(self.organization.code, self.people_group.pk),
            ),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        signal.assert_called_with(self.people_group.pk)
