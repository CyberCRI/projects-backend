from unittest.mock import call, patch

from django.test import override_settings
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
        cls.superadmin = UserFactory(groups=[get_superadmins_group()])
        cls.people_group = PeopleGroupFactory(organization=cls.organization)
        cls.member_to_remove = UserFactory(groups=[cls.people_group.get_members()])
        cls.member_to_add = UserFactory()

    @staticmethod
    def mocked_update(*args, **kwargs):
        pass

    @patch("django_opensearch_dsl.documents.Document.update")
    @override_settings(OPENSEARCH_DSL_AUTO_REFRESH=True, OPENSEARCH_DSL_AUTOSYNC=True)
    def test_signal_called_on_people_group_create(self, mocked_update):
        mocked_update.side_effect = self.mocked_update

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
        people_group = PeopleGroup.objects.get(id=response.json()["id"])
        mocked_update.assert_has_calls([call(people_group, "index")])

    @patch("django_opensearch_dsl.documents.Document.update")
    @override_settings(OPENSEARCH_DSL_AUTO_REFRESH=True, OPENSEARCH_DSL_AUTOSYNC=True)
    def test_signal_called_on_people_group_update(self, mocked_update):
        mocked_update.side_effect = self.mocked_update

        self.client.force_authenticate(self.superadmin)
        payload = {"name": faker.name()}
        response = self.client.patch(
            reverse(
                "PeopleGroup-detail",
                args=(self.organization.code, self.people_group.id),
            ),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mocked_update.assert_has_calls([call(self.people_group, "index")])

    @patch("django_opensearch_dsl.documents.Document.update")
    @override_settings(OPENSEARCH_DSL_AUTO_REFRESH=True, OPENSEARCH_DSL_AUTOSYNC=True)
    def test_signal_called_on_member_added(self, mocked_update):
        mocked_update.side_effect = self.mocked_update

        self.client.force_authenticate(self.superadmin)
        payload = {"members": [self.member_to_add.id]}
        response = self.client.post(
            reverse(
                "PeopleGroup-add-member",
                args=(self.organization.code, self.people_group.id),
            ),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        mocked_update.assert_has_calls([call(self.people_group, "index")])

    @patch("django_opensearch_dsl.documents.Document.update")
    @override_settings(OPENSEARCH_DSL_AUTO_REFRESH=True, OPENSEARCH_DSL_AUTOSYNC=True)
    def test_signal_called_on_member_removed(self, mocked_update):
        mocked_update.side_effect = self.mocked_update

        self.client.force_authenticate(self.superadmin)
        payload = {
            "users": [self.member_to_remove.id],
        }
        response = self.client.post(
            reverse(
                "PeopleGroup-remove-member",
                args=(self.organization.code, self.people_group.id),
            ),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        mocked_update.assert_has_calls([call(self.people_group, "index")])
