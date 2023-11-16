from datetime import datetime

from django.urls import reverse
from django.utils.timezone import make_aware
from faker import Faker

from apps.accounts.factories import PeopleGroupFactory, UserFactory
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase
from apps.invitations.factories import InvitationFactory
from apps.organizations.factories import OrganizationFactory

faker = Faker()


class InvitationNoPermissionTestCase(JwtAPITestCase):
    def test_create(self):
        organization = OrganizationFactory()
        people_group = PeopleGroupFactory(organization=organization)
        user = UserFactory()
        self.client.force_authenticate(user)
        response = self.client.post(
            reverse("Invitation-list", args=(organization.code,)),
            data={
                "people_group_id": people_group.id,
                "description": faker.text(),
                "expire_at": make_aware(faker.date_time()),
            },
        )
        assert response.status_code == 403

    def test_list(self):
        organization = OrganizationFactory()
        InvitationFactory.create_batch(size=3, organization=organization)
        user = UserFactory()
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("Invitation-list", args=(organization.code,))
        )
        assert response.status_code == 200
        assert response.data["count"] == 3

    def test_retrieve(self):
        organization = OrganizationFactory()
        invitation = InvitationFactory(organization=organization)
        user = UserFactory()
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse(
                "Invitation-detail",
                args=(
                    organization.code,
                    invitation.id,
                ),
            )
        )
        assert response.status_code == 200

    def test_update(self):
        organization = OrganizationFactory()
        invitation = InvitationFactory(organization=organization)
        user = UserFactory()
        self.client.force_authenticate(user)
        response = self.client.patch(
            reverse(
                "Invitation-detail",
                args=(
                    organization.code,
                    invitation.id,
                ),
            ),
            data={"description": faker.text()},
        )
        assert response.status_code == 403

    def test_delete(self):
        organization = OrganizationFactory()
        invitation = InvitationFactory(organization=organization)
        user = UserFactory()
        self.client.force_authenticate(user)
        response = self.client.delete(
            reverse(
                "Invitation-detail",
                args=(
                    organization.code,
                    invitation.id,
                ),
            ),
        )
        assert response.status_code == 403


class InvitationBasePermissionTestCase(JwtAPITestCase):
    def test_create(self):
        organization = OrganizationFactory()
        people_group = PeopleGroupFactory(organization=organization)
        user = UserFactory(permissions=[("invitations.add_invitation", None)])
        self.client.force_authenticate(user)
        response = self.client.post(
            reverse("Invitation-list", args=(organization.code,)),
            data={
                "people_group_id": people_group.id,
                "expire_at": make_aware(faker.date_time()),
                "description": faker.text(),
            },
        )
        assert response.status_code == 201
        content = response.json()
        assert content["organization"] == organization.code

    def test_update(self):
        organization = OrganizationFactory()
        invitation = InvitationFactory(organization=organization)
        user = UserFactory(permissions=[("invitations.change_invitation", None)])
        self.client.force_authenticate(user)
        response = self.client.patch(
            reverse(
                "Invitation-detail",
                args=(
                    organization.code,
                    invitation.id,
                ),
            ),
            data={"description": faker.text()},
        )
        assert response.status_code == 200

    def test_delete(self):
        organization = OrganizationFactory()
        invitation = InvitationFactory(organization=organization)
        user = UserFactory(permissions=[("invitations.delete_invitation", None)])
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
        assert response.status_code == 204


class InvitationOrganizationPermissionTestCase(JwtAPITestCase):
    def test_create(self):
        organization = OrganizationFactory()
        people_group = PeopleGroupFactory(organization=organization)
        user = UserFactory(permissions=[("organizations.add_invitation", organization)])
        self.client.force_authenticate(user)
        response = self.client.post(
            reverse("Invitation-list", args=(organization.code,)),
            data={
                "people_group_id": people_group.id,
                "expire_at": make_aware(faker.date_time()),
                "description": faker.text(),
            },
        )
        assert response.status_code == 201
        content = response.json()
        assert content["organization"] == organization.code

    def test_update(self):
        organization = OrganizationFactory()
        invitation = InvitationFactory(organization=organization)
        user = UserFactory(
            permissions=[("organizations.change_invitation", organization)]
        )
        self.client.force_authenticate(user)
        response = self.client.patch(
            reverse(
                "Invitation-detail",
                args=(
                    organization.code,
                    invitation.id,
                ),
            ),
            data={"description": faker.text()},
        )
        assert response.status_code == 200

    def test_delete(self):
        organization = OrganizationFactory()
        invitation = InvitationFactory(organization=organization)
        user = UserFactory(
            permissions=[("organizations.delete_invitation", organization)]
        )
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
        assert response.status_code == 204


class InvitationOwnerPermissionTestCase(JwtAPITestCase):
    def test_update(self):
        organization = OrganizationFactory()
        invitation = InvitationFactory(organization=organization)
        user = invitation.owner
        self.client.force_authenticate(user)
        response = self.client.patch(
            reverse(
                "Invitation-detail",
                args=(
                    organization.code,
                    invitation.id,
                ),
            ),
            data={"description": faker.text()},
        )
        assert response.status_code == 200

    def test_delete(self):
        organization = OrganizationFactory()
        invitation = InvitationFactory(organization=organization)
        user = invitation.owner
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
        assert response.status_code == 204


class InvitationTestCase(JwtAPITestCase):
    def test_list_with_hierarchy(self):
        parent = OrganizationFactory()
        organization = OrganizationFactory(parent=parent)
        child = OrganizationFactory(parent=organization)
        invitations = InvitationFactory.create_batch(size=3, organization=organization)
        InvitationFactory.create_batch(size=3, organization=child)
        InvitationFactory.create_batch(size=3, organization=parent)
        InvitationFactory.create_batch(size=3)
        user = UserFactory()
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("Invitation-list", args=(organization.code,))
        )
        assert response.status_code == 200
        assert response.data["count"] == 3
        assert {i["id"] for i in response.data["results"]} == {
            i.id for i in invitations
        }

    def test_create_people_group_in_other_organization(self):
        organization = OrganizationFactory()
        people_group = PeopleGroupFactory()
        user = UserFactory(permissions=[("invitations.add_invitation", None)])
        self.client.force_authenticate(user)
        response = self.client.post(
            reverse("Invitation-list", args=(organization.code,)),
            data={
                "people_group_id": people_group.id,
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
        organization = OrganizationFactory()
        people_group = PeopleGroupFactory(organization=organization)
        invitation = InvitationFactory(
            organization=organization, people_group=people_group
        )
        user = UserFactory(permissions=[("invitations.change_invitation", None)])
        self.client.force_authenticate(user)
        response = self.client.patch(
            reverse(
                "Invitation-detail",
                args=(
                    organization.code,
                    invitation.id,
                ),
            ),
            data={"people_group_id": PeopleGroupFactory().id},
        )
        assert response.status_code == 400
        content = response.json()
        assert (
            content["people_group_id"][0]
            == "People group must belong to the invitation's organization."
        )

    def test_update_organization(self):
        organization = OrganizationFactory()
        invitation = InvitationFactory(organization=organization)
        user = UserFactory(permissions=[("invitations.change_invitation", None)])
        self.client.force_authenticate(user)
        response = self.client.patch(
            reverse(
                "Invitation-detail",
                args=(
                    organization.code,
                    invitation.id,
                ),
            ),
            data={"organization": OrganizationFactory().code},
        )
        assert response.status_code == 400
        assert response.json() == ["Cannot change the organization of an invitation."]

    def test_create_with_org_in_payload(self):
        organization = OrganizationFactory()
        people_group = PeopleGroupFactory(organization=organization)
        user = UserFactory(permissions=[("invitations.add_invitation", None)])
        self.client.force_authenticate(user)
        response = self.client.post(
            reverse("Invitation-list", args=(organization.code,)),
            data={
                "people_group_id": people_group.id,
                "expire_at": make_aware(faker.date_time()),
                "description": faker.text(),
                "organization": OrganizationFactory().code,
            },
        )
        assert response.status_code == 201
        content = response.json()
        assert content["organization"] == organization.code

    def test_order_by_expire_at(self):
        organization = OrganizationFactory()
        invitation_a = InvitationFactory(
            organization=organization, expire_at=make_aware(datetime(2030, 1, 1))
        )
        invitation_b = InvitationFactory(
            organization=organization, expire_at=make_aware(datetime(2030, 1, 2))
        )
        invitation_c = InvitationFactory(
            organization=organization, expire_at=make_aware(datetime(2030, 1, 3))
        )
        user = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("Invitation-list", args=(organization.code,)),
            data={"ordering": "expire_at"},
        )
        assert response.status_code == 200
        content = response.json()
        assert content["count"] == 3
        assert content["results"][0]["id"] == invitation_a.id
        assert content["results"][1]["id"] == invitation_b.id
        assert content["results"][2]["id"] == invitation_c.id
        response = self.client.get(
            reverse("Invitation-list", args=(organization.code,)),
            data={"ordering": "-expire_at"},
        )
        assert response.status_code == 200
        content = response.json()
        assert content["count"] == 3
        assert content["results"][0]["id"] == invitation_c.id
        assert content["results"][1]["id"] == invitation_b.id
        assert content["results"][2]["id"] == invitation_a.id

    def test_order_by_people_group(self):
        organization = OrganizationFactory()
        people_group_a = PeopleGroupFactory(organization=organization, name="A")
        people_group_b = PeopleGroupFactory(organization=organization, name="B")
        people_group_c = PeopleGroupFactory(organization=organization, name="C")
        invitation_a = InvitationFactory(
            organization=organization, people_group=people_group_a
        )
        invitation_b = InvitationFactory(
            organization=organization, people_group=people_group_b
        )
        invitation_c = InvitationFactory(
            organization=organization, people_group=people_group_c
        )
        user = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("Invitation-list", args=(organization.code,)),
            data={"ordering": "people_group__name"},
        )
        assert response.status_code == 200
        content = response.json()
        assert content["count"] == 3
        assert content["results"][0]["id"] == invitation_a.id
        assert content["results"][1]["id"] == invitation_b.id
        assert content["results"][2]["id"] == invitation_c.id
        response = self.client.get(
            reverse("Invitation-list", args=(organization.code,)),
            data={"ordering": "-people_group__name"},
        )
        assert response.status_code == 200
        content = response.json()
        assert content["count"] == 3
        assert content["results"][0]["id"] == invitation_c.id
        assert content["results"][1]["id"] == invitation_b.id
        assert content["results"][2]["id"] == invitation_a.id

    def test_order_by_owner_given_name(self):
        organization = OrganizationFactory()
        user_a = UserFactory(given_name="A")
        user_b = UserFactory(given_name="B")
        user_c = UserFactory(given_name="C")
        invitation_a = InvitationFactory(organization=organization, owner=user_a)
        invitation_b = InvitationFactory(organization=organization, owner=user_b)
        invitation_c = InvitationFactory(organization=organization, owner=user_c)
        user = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("Invitation-list", args=(organization.code,)),
            data={"ordering": "owner__given_name"},
        )
        assert response.status_code == 200
        content = response.json()
        assert content["count"] == 3
        assert content["results"][0]["id"] == invitation_a.id
        assert content["results"][1]["id"] == invitation_b.id
        assert content["results"][2]["id"] == invitation_c.id
        response = self.client.get(
            reverse("Invitation-list", args=(organization.code,)),
            data={"ordering": "-owner__given_name"},
        )
        assert response.status_code == 200
        content = response.json()
        assert content["count"] == 3
        assert content["results"][0]["id"] == invitation_c.id
        assert content["results"][1]["id"] == invitation_b.id
        assert content["results"][2]["id"] == invitation_a.id

    def test_order_by_owner_family_name(self):
        organization = OrganizationFactory()
        user_a = UserFactory(family_name="A")
        user_b = UserFactory(family_name="B")
        user_c = UserFactory(family_name="C")
        invitation_a = InvitationFactory(organization=organization, owner=user_a)
        invitation_b = InvitationFactory(organization=organization, owner=user_b)
        invitation_c = InvitationFactory(organization=organization, owner=user_c)
        user = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("Invitation-list", args=(organization.code,)),
            data={"ordering": "owner__family_name"},
        )
        assert response.status_code == 200
        content = response.json()
        assert content["count"] == 3
        assert content["results"][0]["id"] == invitation_a.id
        assert content["results"][1]["id"] == invitation_b.id
        assert content["results"][2]["id"] == invitation_c.id
        response = self.client.get(
            reverse("Invitation-list", args=(organization.code,)),
            data={"ordering": "-owner__family_name"},
        )
        assert response.status_code == 200
        content = response.json()
        assert content["count"] == 3
        assert content["results"][0]["id"] == invitation_c.id
        assert content["results"][1]["id"] == invitation_b.id
        assert content["results"][2]["id"] == invitation_a.id
