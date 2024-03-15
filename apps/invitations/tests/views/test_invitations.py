from datetime import datetime

from django.urls import reverse
from django.utils.timezone import make_aware
from faker import Faker
from parameterized import parameterized
from rest_framework import status

from apps.accounts.factories import PeopleGroupFactory, UserFactory
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase, TestRoles
from apps.invitations.factories import InvitationFactory
from apps.invitations.models import Invitation
from apps.organizations.factories import OrganizationFactory

faker = Faker()


class CreateInvitationTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.people_group = PeopleGroupFactory(organization=cls.organization)

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_201_CREATED),
            (TestRoles.ORG_ADMIN, status.HTTP_201_CREATED),
            (TestRoles.ORG_FACILITATOR, status.HTTP_201_CREATED),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_create_invitation(self, role, expected_code):
        organization = self.organization
        user = self.get_parameterized_test_user(role, instances=[organization])
        self.client.force_authenticate(user)
        payload = {
            "people_group_id": self.people_group.id,
            "expire_at": make_aware(faker.date_time()),
            "description": faker.text(),
        }
        response = self.client.post(
            reverse("Invitation-list", args=(organization.code,)),
            data=payload,
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_201_CREATED:
            content = response.json()
            self.assertEqual(content["people_group"]["id"], payload["people_group_id"])
            self.assertEqual(content["description"], payload["description"])


class UpdateInvitationTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.people_group = PeopleGroupFactory(organization=cls.organization)
        cls.invitation = InvitationFactory(
            organization=cls.organization, people_group=cls.people_group
        )

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_ADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_FACILITATOR, status.HTTP_200_OK),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_update_invitation(self, role, expected_code):
        user = self.get_parameterized_test_user(role, instances=[self.organization])
        self.client.force_authenticate(user)
        payload = {"description": faker.text()}
        response = self.client.patch(
            reverse(
                "Invitation-detail",
                args=(
                    self.organization.code,
                    self.invitation.id,
                ),
            ),
            data=payload,
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_200_OK:
            content = response.json()
            self.assertEqual(content["description"], payload["description"])


class DeleteInvitationTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.people_group = PeopleGroupFactory(organization=cls.organization)

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_ADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_FACILITATOR, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_delete_invitation(self, role, expected_code):
        organization = self.organization
        invitation = InvitationFactory(
            organization=organization, people_group=self.people_group
        )
        user = self.get_parameterized_test_user(role, instances=[organization])
        self.client.force_authenticate(user)
        response = self.client.delete(
            reverse(
                "Invitation-detail",
                args=(
                    organization.code,
                    invitation.id,
                ),
            )
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_204_NO_CONTENT:
            self.assertFalse(Invitation.objects.filter(id=invitation.id).exists())


class ValidateInvitationTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.organization_2 = OrganizationFactory()
        cls.people_group = PeopleGroupFactory(organization=cls.organization)
        cls.people_group_2 = PeopleGroupFactory(organization=cls.organization_2)
        cls.user = UserFactory(groups=[get_superadmins_group()])

    def test_create_people_group_in_other_organization(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            reverse("Invitation-list", args=(self.organization.code,)),
            data={
                "people_group_id": self.people_group_2.id,
                "expire_at": make_aware(faker.date_time()),
                "description": faker.text(),
            },
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertApiValidationError(
            response,
            {
                "people_group_id": [
                    "People group must belong to the invitation's organization"
                ]
            },
        )

    def test_update_people_group_in_other_organization(self):
        invitation = InvitationFactory(
            organization=self.organization, people_group=self.people_group
        )
        self.client.force_authenticate(self.user)
        response = self.client.patch(
            reverse(
                "Invitation-detail",
                args=(
                    self.organization.code,
                    invitation.id,
                ),
            ),
            data={"people_group_id": self.people_group_2.id},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertApiValidationError(
            response,
            {
                "people_group_id": [
                    "People group must belong to the invitation's organization"
                ]
            },
        )

    def test_update_organization(self):
        invitation = InvitationFactory(organization=self.organization)
        self.client.force_authenticate(self.user)
        response = self.client.patch(
            reverse(
                "Invitation-detail",
                args=(
                    self.organization.code,
                    invitation.id,
                ),
            ),
            data={"organization": self.organization_2.code},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertApiValidationError(
            response,
            {"organization": ["You cannot change the organization of an invitation"]},
        )

    def test_create_with_org_in_payload(self):
        self.client.force_authenticate(self.user)
        response = self.client.post(
            reverse("Invitation-list", args=(self.organization.code,)),
            data={
                "people_group_id": self.people_group.id,
                "expire_at": make_aware(faker.date_time()),
                "description": faker.text(),
                "organization": self.organization_2.code,
            },
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        content = response.json()
        self.assertEqual(content["organization"], self.organization.code)


class OrderInvitationTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.people_group_a = PeopleGroupFactory(organization=cls.organization, name="A")
        cls.people_group_b = PeopleGroupFactory(organization=cls.organization, name="B")
        cls.people_group_c = PeopleGroupFactory(organization=cls.organization, name="C")
        user_a = UserFactory(given_name="A", family_name="A")
        user_b = UserFactory(given_name="B", family_name="B")
        user_c = UserFactory(given_name="C", family_name="C")
        cls.invitation_a = InvitationFactory(
            organization=cls.organization,
            people_group=cls.people_group_a,
            owner=user_a,
            expire_at=make_aware(datetime(2030, 1, 1)),
        )
        cls.invitation_b = InvitationFactory(
            organization=cls.organization,
            people_group=cls.people_group_b,
            owner=user_b,
            expire_at=make_aware(datetime(2030, 1, 2)),
        )
        cls.invitation_c = InvitationFactory(
            organization=cls.organization,
            people_group=cls.people_group_c,
            owner=user_c,
            expire_at=make_aware(datetime(2030, 1, 3)),
        )
        cls.superadmin = UserFactory(groups=[get_superadmins_group()])

    def setUp(self) -> None:
        super().setUp()
        self.client.force_authenticate(self.superadmin)

    def test_order_by_expire_at(self):
        response = self.client.get(
            reverse("Invitation-list", args=(self.organization.code,))
            + "?ordering=expire_at"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["count"], 3)
        self.assertEqual(content["results"][0]["id"], self.invitation_a.id)
        self.assertEqual(content["results"][1]["id"], self.invitation_b.id)
        self.assertEqual(content["results"][2]["id"], self.invitation_c.id)

    def test_order_by_expire_at_reverse(self):
        response = self.client.get(
            reverse("Invitation-list", args=(self.organization.code,))
            + "?ordering=-expire_at"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["count"], 3)
        self.assertEqual(content["results"][0]["id"], self.invitation_c.id)
        self.assertEqual(content["results"][1]["id"], self.invitation_b.id)
        self.assertEqual(content["results"][2]["id"], self.invitation_a.id)

    def test_order_by_people_group_name(self):
        response = self.client.get(
            reverse("Invitation-list", args=(self.organization.code,))
            + "?ordering=people_group__name"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["count"], 3)
        self.assertEqual(content["results"][0]["id"], self.invitation_a.id)
        self.assertEqual(content["results"][1]["id"], self.invitation_b.id)
        self.assertEqual(content["results"][2]["id"], self.invitation_c.id)

    def test_order_by_people_group_name_reverse(self):
        response = self.client.get(
            reverse("Invitation-list", args=(self.organization.code,))
            + "?ordering=-people_group__name"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["count"], 3)
        self.assertEqual(content["results"][0]["id"], self.invitation_c.id)
        self.assertEqual(content["results"][1]["id"], self.invitation_b.id)
        self.assertEqual(content["results"][2]["id"], self.invitation_a.id)

    def test_order_by_owner_given_name(self):
        response = self.client.get(
            reverse("Invitation-list", args=(self.organization.code,))
            + "?ordering=owner__given_name"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["count"], 3)
        self.assertEqual(content["results"][0]["id"], self.invitation_a.id)
        self.assertEqual(content["results"][1]["id"], self.invitation_b.id)
        self.assertEqual(content["results"][2]["id"], self.invitation_c.id)

    def test_order_by_owner_given_name_reverse(self):
        response = self.client.get(
            reverse("Invitation-list", args=(self.organization.code,))
            + "?ordering=-owner__given_name"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["count"], 3)
        self.assertEqual(content["results"][0]["id"], self.invitation_c.id)
        self.assertEqual(content["results"][1]["id"], self.invitation_b.id)
        self.assertEqual(content["results"][2]["id"], self.invitation_a.id)

    def test_order_by_owner_family_name(self):
        response = self.client.get(
            reverse("Invitation-list", args=(self.organization.code,))
            + "?ordering=owner__family_name"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["count"], 3)
        self.assertEqual(content["results"][0]["id"], self.invitation_a.id)
        self.assertEqual(content["results"][1]["id"], self.invitation_b.id)
        self.assertEqual(content["results"][2]["id"], self.invitation_c.id)

    def test_order_by_owner_family_name_reverse(self):
        response = self.client.get(
            reverse("Invitation-list", args=(self.organization.code,))
            + "?ordering=-owner__family_name"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["count"], 3)
        self.assertEqual(content["results"][0]["id"], self.invitation_c.id)
        self.assertEqual(content["results"][1]["id"], self.invitation_b.id)
        self.assertEqual(content["results"][2]["id"], self.invitation_a.id)
