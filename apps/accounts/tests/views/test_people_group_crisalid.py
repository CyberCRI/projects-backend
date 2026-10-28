from django.urls import reverse
from faker import Faker
from parameterized import parameterized
from rest_framework import status

from apps.accounts.factories import PeopleGroupFactory, UserFactory
from apps.accounts.models import PeopleGroup
from apps.commons.test import JwtAPITestCase, TestRoles
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory
from services.crisalid.factories import StructureFactory
from services.crisalid.utils.structures import sync_structures

faker = Faker()


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


class ProtectedCrisalidPeopleGroupTestCase(CrisalidPeopleGroupTestCase):
    @parameterized.expand(
        [
            (TestRoles.SUPERADMIN, status.HTTP_403_FORBIDDEN),
            (TestRoles.ORG_ADMIN, status.HTTP_403_FORBIDDEN),
            (TestRoles.GROUP_MANAGER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_update_crisalid_people_group(self, role, expected_code):
        user = self.get_parameterized_test_user(role, instances=[self.people_group])
        self.client.force_authenticate(user)
        response = self.client.patch(
            reverse(
                "PeopleGroup-detail",
                args=(self.organization.code, self.people_group.pk),
            ),
            {"description": faker.text()},
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_403_FORBIDDEN:
            self.assertApiPermissionError(response, "This group is managed by Crisalid")

    @parameterized.expand(
        [
            (TestRoles.SUPERADMIN, status.HTTP_403_FORBIDDEN),
            (TestRoles.ORG_ADMIN, status.HTTP_403_FORBIDDEN),
            (TestRoles.GROUP_MANAGER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_delete_crisalid_people_group(self, role, expected_code):
        user = self.get_parameterized_test_user(role, instances=[self.people_group])
        self.client.force_authenticate(user)
        response = self.client.delete(
            reverse(
                "PeopleGroup-detail",
                args=(self.organization.code, self.people_group.pk),
            )
        )
        self.assertEqual(response.status_code, expected_code)

    @parameterized.expand(
        [
            (TestRoles.SUPERADMIN, status.HTTP_403_FORBIDDEN),
            (TestRoles.ORG_ADMIN, status.HTTP_403_FORBIDDEN),
            (TestRoles.GROUP_MANAGER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_add_member_crisalid_people_group(self, role, expected_code):
        user = self.get_parameterized_test_user(role, instances=[self.people_group])
        self.client.force_authenticate(user)
        member = UserFactory()
        response = self.client.post(
            reverse(
                "PeopleGroup-add-member",
                args=(self.organization.code, self.people_group.pk),
            ),
            {"members": [member.id]},
        )
        self.assertEqual(response.status_code, expected_code)

    @parameterized.expand(
        [
            (TestRoles.SUPERADMIN, status.HTTP_403_FORBIDDEN),
            (TestRoles.ORG_ADMIN, status.HTTP_403_FORBIDDEN),
            (TestRoles.GROUP_MANAGER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_remove_member_crisalid_people_group(self, role, expected_code):
        user = self.get_parameterized_test_user(role, instances=[self.people_group])
        self.client.force_authenticate(user)
        member = UserFactory()
        self.people_group.members.add(member)
        response = self.client.post(
            reverse(
                "PeopleGroup-remove-member",
                args=(self.organization.code, self.people_group.pk),
            ),
            {"users": [member.id]},
        )
        self.assertEqual(response.status_code, expected_code)

    @parameterized.expand(
        [
            (TestRoles.SUPERADMIN, status.HTTP_403_FORBIDDEN),
            (TestRoles.ORG_ADMIN, status.HTTP_403_FORBIDDEN),
            (TestRoles.GROUP_MANAGER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_add_featured_project_crisalid_people_group(self, role, expected_code):
        user = self.get_parameterized_test_user(role, instances=[self.people_group])
        self.client.force_authenticate(user)
        project = ProjectFactory(organizations=[self.organization])
        response = self.client.post(
            reverse(
                "PeopleGroup-add-featured-project",
                args=(self.organization.code, self.people_group.pk),
            ),
            {"featured_projects": [project.pk]},
        )
        self.assertEqual(response.status_code, expected_code)

    def test_add_role_crisalid_people_group(self):
        user = self.get_parameterized_test_user(
            TestRoles.ORG_ADMIN, instances=[self.people_group]
        )
        self.client.force_authenticate(user)
        member = UserFactory()
        response = self.client.patch(
            reverse("ProjectUser-detail", args=(member.id,)),
            {"roles_to_add": [self.people_group.get_members().name]},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertNotIn(member, self.people_group.members.all())

    def test_update_other_people_group(self):
        user = self.get_parameterized_test_user(
            TestRoles.ORG_ADMIN, instances=[self.people_group]
        )
        self.client.force_authenticate(user)
        people_group = PeopleGroupFactory(organization=self.organization)
        response = self.client.patch(
            reverse(
                "PeopleGroup-detail",
                args=(self.organization.code, people_group.pk),
            ),
            {"description": faker.text()},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class CrisalidUpdatePeopleGroupTestCase(CrisalidPeopleGroupTestCase):
    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_ADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
            (TestRoles.GROUP_MANAGER, status.HTTP_200_OK),
            (TestRoles.GROUP_MEMBER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_crisalid_update(self, role, expected_code):
        user = self.get_parameterized_test_user(role, instances=[self.people_group])
        self.client.force_authenticate(user)
        parent = PeopleGroupFactory(organization=self.organization)
        payload = {
            "short_description": faker.sentence(),
            "description": faker.text(),
            "name": "new name",
            "parent": parent.pk,
        }
        response = self.client.patch(
            reverse(
                "PeopleGroup-crisalid-update",
                args=(self.organization.code, self.people_group.pk),
            ),
            payload,
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_200_OK:
            self.assertEqual(
                response.data["short_description"], payload["short_description"]
            )
            # name, description and parent are managed by crisalid
            self.people_group.refresh_from_db()
            self.assertEqual(self.people_group.name, self.structure.name)
            self.assertEqual(self.people_group.description, self.structure.description)
            self.assertEqual(self.people_group.parent, self.root)

    def test_crisalid_update_not_structure(self):
        user = self.get_parameterized_test_user(
            TestRoles.ORG_ADMIN, instances=[self.people_group]
        )
        self.client.force_authenticate(user)
        people_group = PeopleGroupFactory(organization=self.organization)
        response = self.client.patch(
            reverse(
                "PeopleGroup-crisalid-update",
                args=(self.organization.code, people_group.pk),
            ),
            {"description": faker.text()},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class CrisalidPeopleGroupMembersTestCase(CrisalidPeopleGroupTestCase):
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
        self.assertEqual(
            content["structure"]["crisalid_uid"], self.structure.crisalid_uid
        )
        # crisalid modules are in structure modules, not in group modules
        self.assertNotIn("sub_structures", content["modules"])

        people_group = PeopleGroupFactory(organization=self.organization)
        response = self.client.get(
            reverse(
                "PeopleGroup-detail", args=(self.organization.code, people_group.pk)
            )
        )
        self.assertIsNone(response.json()["structure"])
