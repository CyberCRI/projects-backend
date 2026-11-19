from django.urls import reverse

from apps.accounts.factories import PeopleGroupFactory
from apps.accounts.models import PeopleGroup
from apps.commons.test import JwtAPITestCase, TestRoles
from apps.organizations.factories import OrganizationFactory
from services.crisalid.factories import StructureFactory
from services.crisalid.utils.structures import sync_structures


class CrisalidPeopleGroupTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.root = PeopleGroup.update_or_create_root(cls.organization)
        cls.structure = StructureFactory(organization=cls.organization)
        sync_structures([cls.structure])
        cls.structure.refresh_from_db()
        cls.people_group = cls.structure.people_group

    def test_retrieve_structure(self):
        user = self.get_parameterized_test_user(
            TestRoles.SUPERADMIN, instances=[self.people_group]
        )
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse(
                "PeopleGroup-detail",
                args=(self.organization.code, self.people_group.pk),
            )
        )
        content = response.json()
        self.assertEqual(content["structure"]["id"], self.structure.id)
        # crisalid modules are in structure modules, not in group modules
        self.assertNotIn("sub_structures", content["modules"])

        people_group = PeopleGroupFactory(organization=self.organization)
        response = self.client.get(
            reverse(
                "PeopleGroup-detail", args=(self.organization.code, people_group.pk)
            )
        )
        self.assertIsNone(response.json()["structure"])
