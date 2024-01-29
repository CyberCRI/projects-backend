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
        assert response.status_code == expected_code
        if expected_code == status.HTTP_201_CREATED:
            content = response.json()
            assert content["people_group"]["id"] == payload["people_group_id"]
            assert content["description"] == payload["description"]


class UpdateInvitationTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.people_group = PeopleGroupFactory(organization=cls.organization)

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
        organization = self.organization
        invitation = InvitationFactory(
            organization=organization, people_group=self.people_group
        )
        user = self.get_parameterized_test_user(role, instances=[organization])
        self.client.force_authenticate(user)
        payload = {"description": faker.text()}
        response = self.client.patch(
            reverse(
                "Invitation-detail",
                args=(
                    organization.code,
                    invitation.id,
                ),
            ),
            data=payload,
        )
        assert response.status_code == expected_code
        if expected_code == status.HTTP_200_OK:
            content = response.json()
            assert content["description"] == payload["description"]


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
        assert response.status_code == expected_code
        if expected_code == status.HTTP_204_NO_CONTENT:
            assert not Invitation.objects.filter(id=invitation.id).exists()


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
        assert response.status_code == 400
        content = response.json()
        assert (
            content["people_group_id"][0]
            == "People group must belong to the invitation's organization."
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
        assert response.status_code == 400
        content = response.json()
        assert (
            content["people_group_id"][0]
            == "People group must belong to the invitation's organization."
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
        assert response.status_code == 400
        assert response.json() == ["Cannot change the organization of an invitation."]

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
        assert response.status_code == 201
        content = response.json()
        assert content["organization"] == self.organization.code


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
        cls.user = UserFactory(groups=[get_superadmins_group()])

    @parameterized.expand(
        [
            ("expire_at",),
            ("people_group__name",),
            ("owner__given_name",),
            ("owner__family_name",),
        ]
    )
    def test_order_invitations(self, ordering_field):
        self.client.force_authenticate(self.user)
        response = self.client.get(
            reverse("Invitation-list", args=(self.organization.code,)),
            data={"ordering": ordering_field},
        )
        assert response.status_code == 200
        content = response.json()
        assert content["count"] == 3
        assert content["results"][0]["id"] == self.invitation_a.id
        assert content["results"][1]["id"] == self.invitation_b.id
        assert content["results"][2]["id"] == self.invitation_c.id
        response = self.client.get(
            reverse("Invitation-list", args=(self.organization.code,)),
            data={"ordering": f"-{ordering_field}"},
        )
        assert response.status_code == 200
        content = response.json()
        assert content["count"] == 3
        assert content["results"][0]["id"] == self.invitation_c.id
        assert content["results"][1]["id"] == self.invitation_b.id
        assert content["results"][2]["id"] == self.invitation_a.id
