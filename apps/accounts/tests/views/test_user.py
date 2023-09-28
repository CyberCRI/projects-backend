import datetime

import pytest
from django.urls import reverse
from django.utils.timezone import make_aware
from faker import Faker
from guardian.shortcuts import assign_perm

from apps.accounts.factories import PeopleGroupFactory, SeedUserFactory, UserFactory
from apps.accounts.models import ProjectUser
from apps.accounts.utils import get_default_group, get_superadmins_group
from apps.commons.test import JwtAPITestCase
from apps.invitations.factories import InvitationFactory
from apps.notifications.factories import NotificationFactory
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory

faker = Faker()


@pytest.mark.django_db
class UsersTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        # Overwrite this method because it creates a user and makes test_list fail
        pass

    def url(self, pk=None):
        if pk:
            return reverse("ProjectUser-detail", args=[pk])
        return reverse("ProjectUser-list")

    # SUCCESS
    def test_list(self):
        users = UserFactory.create_batch(size=5)
        self.client.force_authenticate(user=users[0])
        response = self.client.get(self.url())
        assert response.status_code == 200
        assert response.data["count"] == 5

    def test_retrieve(self):
        users = UserFactory.create_batch(size=2)
        organization = OrganizationFactory()
        organization.users.add(*users)
        self.client.force_authenticate(user=users[0])
        response = self.client.get(self.url(users[1].keycloak_id))

        assert response.status_code == 200
        assert "privacy_settings" in response.data

    def test_update_200(self):
        user = SeedUserFactory()
        self.client.force_authenticate(user)
        payload = {"pronouns": "She / Her", "sdgs": [1, 2, 3]}
        response = self.client.patch(
            self.url(user.keycloak_id),
            payload,
        )
        assert response.status_code == 200
        assert response.data["pronouns"] == payload["pronouns"]
        assert response.data["sdgs"] == payload["sdgs"]

    def test_update_403(self):
        user = UserFactory()
        self.client.force_authenticate(user=UserFactory())
        response = self.client.patch(
            self.url(user.keycloak_id),
            {"pronouns": "She / Her"},
        )
        assert response.status_code == 403

    def test_notifications_count(self):
        user = UserFactory()
        NotificationFactory.create_batch(5, receiver=user, is_viewed=False)
        NotificationFactory(receiver=user, is_viewed=True)
        NotificationFactory()
        self.client.force_authenticate(user)
        response = self.client.get(self.url(user.keycloak_id))
        assert response.status_code == 200
        assert response.data["notifications"] == 5

    def test_language_from_organization(self):
        user = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(user)
        organization = OrganizationFactory(language="fr")
        payload = {
            "people_id": faker.uuid4(),
            "email": f"{faker.uuid4()}@yopmail.com",
            "personal_email": f"{faker.uuid4()}@yopmail.com",
            "given_name": faker.first_name(),
            "family_name": faker.last_name(),
            "roles_to_add": [organization.get_users().name],
        }
        response = self.client.post(reverse("ProjectUser-list"), data=payload)
        assert response.status_code == 201
        assert response.data["language"] == "fr"

    def test_get_current_org_role(self):
        users = UserFactory.create_batch(3)
        admins = UserFactory.create_batch(3)
        facilitators = UserFactory.create_batch(3)
        UserFactory.create_batch(3)
        organization = OrganizationFactory()
        organization.admins.first().delete()  # created by factory
        organization.users.add(*users)
        organization.admins.add(*admins)
        organization.facilitators.add(*facilitators)
        url = reverse("ProjectUser-list")
        url += f"?current_org_pk={organization.pk}"
        response = self.client.get(url)
        assert response.status_code == 200
        assert response.data["count"] == 12
        for user in response.data["results"]:
            if user["keycloak_id"] in [u.keycloak_id for u in admins]:
                assert user["current_org_role"] == "admins"
            elif user["keycloak_id"] in [u.keycloak_id for u in facilitators]:
                assert user["current_org_role"] == "facilitators"
            elif user["keycloak_id"] in [u.keycloak_id for u in users]:
                assert user["current_org_role"] == "users"
            else:
                assert user["current_org_role"] is None

    def test_get_current_org_role_two_roles(self):
        organization = OrganizationFactory()
        organization.admins.first().delete()  # created by factory
        user = UserFactory()
        organization.users.add(user)
        organization.admins.add(user)
        url = reverse("ProjectUser-list")
        url += f"?current_org_pk={organization.pk}"
        response = self.client.get(url)
        assert response.status_code == 200
        assert response.data["count"] == 1
        assert response.data["results"][0]["current_org_role"] == "admins"

    def test_order_by_job(self):
        user_a = UserFactory(job="A")
        user_b = UserFactory(job="B")
        user_c = UserFactory(job="C")
        response = self.client.get(self.url() + "?ordering=job")
        assert response.status_code == 200
        assert response.data["results"][0]["keycloak_id"] == user_a.keycloak_id
        assert response.data["results"][1]["keycloak_id"] == user_b.keycloak_id
        assert response.data["results"][2]["keycloak_id"] == user_c.keycloak_id
        response = self.client.get(self.url() + "?ordering=-job")
        assert response.status_code == 200
        assert response.data["results"][0]["keycloak_id"] == user_c.keycloak_id
        assert response.data["results"][1]["keycloak_id"] == user_b.keycloak_id
        assert response.data["results"][2]["keycloak_id"] == user_a.keycloak_id

    def test_order_by_role(self):
        organization = OrganizationFactory()
        organization.admins.first().delete()  # created by factory
        user_a = UserFactory()
        user_b = UserFactory()
        user_c = UserFactory()
        user_d = UserFactory()
        organization.admins.add(user_a)
        organization.facilitators.add(user_b)
        organization.users.add(user_c)
        response = self.client.get(
            self.url() + f"?ordering=current_org_role&current_org_pk={organization.pk}"
        )
        assert response.status_code == 200
        assert response.data["results"][0]["keycloak_id"] == user_a.keycloak_id
        assert response.data["results"][1]["keycloak_id"] == user_b.keycloak_id
        assert response.data["results"][2]["keycloak_id"] == user_c.keycloak_id
        assert response.data["results"][3]["keycloak_id"] == user_d.keycloak_id
        response = self.client.get(
            self.url() + f"?ordering=-current_org_role&current_org_pk={organization.pk}"
        )
        assert response.status_code == 200
        assert response.data["results"][0]["keycloak_id"] == user_d.keycloak_id
        assert response.data["results"][1]["keycloak_id"] == user_c.keycloak_id
        assert response.data["results"][2]["keycloak_id"] == user_b.keycloak_id
        assert response.data["results"][3]["keycloak_id"] == user_a.keycloak_id

    def filter_by_role(self):
        organization = OrganizationFactory()
        organization.admins.first().delete()  # created by factory
        user_a = UserFactory()
        user_b = UserFactory()
        user_c = UserFactory()
        user_d = UserFactory()
        organization.admins.add(user_a)
        organization.facilitators.add(user_b)
        organization.users.add(user_c)
        response = self.client.get(
            self.url() + f"?current_org_role=admins&current_org_pk={organization.pk}"
        )
        assert response.status_code == 200
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["keycloak_id"] == user_a.keycloak_id
        response = self.client.get(
            self.url()
            + f"?current_org_role=facilitators&current_org_pk={organization.pk}"
        )
        assert response.status_code == 200
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["keycloak_id"] == user_b.keycloak_id
        response = self.client.get(
            self.url() + f"?current_org_role=users&current_org_pk={organization.pk}"
        )
        assert response.status_code == 200
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["keycloak_id"] == user_c.keycloak_id
        response = self.client.get(
            self.url() + f"?current_org_role=_no_role&current_org_pk={organization.pk}"
        )
        assert response.status_code == 200
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["keycloak_id"] == user_d.keycloak_id

    def test_search_by_job(self):
        params = {
            "given_name": "test",
            "family_name": "test",
            "email": "test@test.com",
        }
        user_a = UserFactory(job="ABCDE", **params)
        user_b = UserFactory(job="VWXYZ", **params)
        user_c = UserFactory(job="FGHIJ", **params)
        response = self.client.get(self.url() + "?search=ABCDE")
        assert response.status_code == 200
        assert response.data["results"][0]["keycloak_id"] == user_a.keycloak_id
        response = self.client.get(self.url() + "?search=VWXYZ")
        assert response.status_code == 200
        assert response.data["results"][0]["keycloak_id"] == user_b.keycloak_id
        response = self.client.get(self.url() + "?search=FGHIJ")
        assert response.status_code == 200
        assert response.data["results"][0]["keycloak_id"] == user_c.keycloak_id

    def test_search_by_people_group(self):
        params = {
            "given_name": "test",
            "family_name": "test",
            "email": "test@test.com",
            "job": "test",
        }
        people_group_a = PeopleGroupFactory(name="ABCDE")
        people_group_b = PeopleGroupFactory(name="VWXYZ")
        people_group_c = PeopleGroupFactory(name="FGHIJ")
        user_a = UserFactory(**params)
        user_b = UserFactory(**params)
        user_c = UserFactory(**params)
        people_group_a.members.add(user_a)
        people_group_b.members.add(user_b)
        people_group_c.members.add(user_c)
        response = self.client.get(self.url() + "?search=ABCDE")
        assert response.status_code == 200
        assert response.data["results"][0]["keycloak_id"] == user_a.keycloak_id
        response = self.client.get(self.url() + "?search=VWXYZ")
        assert response.status_code == 200
        assert response.data["results"][0]["keycloak_id"] == user_b.keycloak_id
        response = self.client.get(self.url() + "?search=FGHIJ")
        assert response.status_code == 200
        assert response.data["results"][0]["keycloak_id"] == user_c.keycloak_id

    def test_search_with_current_org_pk(self):
        organization = OrganizationFactory()
        organization.admins.first().delete()  # created by factory
        params = {
            "given_name": "test",
            "family_name": "test",
            "email": "test@test.com",
        }
        user_a = UserFactory(job="ABCDE", **params)
        user_b = UserFactory(job="VWXYZ", **params)
        user_c = UserFactory(job="FGHIJ", **params)
        response = self.client.get(
            self.url() + f"?search=ABCDE&current_org_pk={organization.pk}"
        )
        assert response.status_code == 200
        assert response.data["results"][0]["keycloak_id"] == user_a.keycloak_id
        response = self.client.get(
            self.url() + f"?search=VWXYZ&current_org_pk={organization.pk}"
        )
        assert response.status_code == 200
        assert response.data["results"][0]["keycloak_id"] == user_b.keycloak_id
        response = self.client.get(
            self.url() + f"?search=FGHIJ&current_org_pk={organization.pk}"
        )
        assert response.status_code == 200
        assert response.data["results"][0]["keycloak_id"] == user_c.keycloak_id

    def test_create_user_group_validation_no_permission(self):
        organization = OrganizationFactory()
        user = UserFactory(permissions=[("accounts.add_projectuser", None)])
        self.client.force_authenticate(user=user)
        payload = {
            "people_id": faker.uuid4(),
            "email": f"{faker.uuid4()}@yopmail.com",
            "personal_email": f"{faker.uuid4()}@yopmail.com",
            "given_name": faker.first_name(),
            "family_name": faker.last_name(),
            "roles_to_add": [organization.get_users().name],
        }
        response = self.client.post(reverse("ProjectUser-list"), data=payload)
        assert response.status_code == 403
        assert f"organization:#{organization.pk}:users" in response.json()["detail"]

    def test_get_slug(self):
        given_name = faker.first_name()
        family_name = faker.last_name()
        user = UserFactory(given_name=given_name, family_name=family_name)
        slug_base = "-".join([given_name.lower(), family_name.lower()])
        assert user.slug == slug_base
        user = UserFactory(given_name=given_name, family_name=family_name)
        assert user.slug == f"{slug_base}-1"
        user = UserFactory(given_name=given_name, family_name=family_name)
        assert user.slug == f"{slug_base}-2"
        user = UserFactory(given_name="", family_name="")
        slug_base = user.email.split("@")[0].lower()
        assert user.slug == slug_base

    def test_multiple_lookups(self):
        user = UserFactory()
        self.client.force_authenticate(user)
        user_2 = UserFactory()
        response = self.client.get(
            reverse("ProjectUser-detail", args=(user_2.keycloak_id,))
        )
        assert response.status_code == 200
        assert response.data["slug"] == user_2.slug
        response = self.client.get(reverse("ProjectUser-detail", args=(user_2.slug,)))
        assert response.status_code == 200
        assert response.data["keycloak_id"] == user_2.keycloak_id


class UserAnonymousTestCase(JwtAPITestCase):
    def test_create_user_anonymous(self):
        response = self.client.post(reverse("ProjectUser-list"))
        assert response.status_code == 401

    def test_check_permissions_anonymous(self):
        user = UserFactory()
        organization = OrganizationFactory()
        permissions = [
            "projects.view_project",
            f"organizations.view_org_project.{organization.pk}",
        ]
        response = self.client.get(
            reverse("ProjectUser-has-permissions", args=(user.keycloak_id,)),
            {"permissions": ",".join(permissions)},
        )
        assert response.status_code == 200
        assert response.json()["result"] is False

        assign_perm("organizations.view_org_project", user, organization)
        response = self.client.get(
            reverse("ProjectUser-has-permissions", args=(user.keycloak_id,)),
            {"permissions": ",".join(permissions)},
        )
        assert response.status_code == 200
        assert response.json()["result"] is True

        assign_perm("projects.view_project", user)
        response = self.client.get(
            reverse("ProjectUser-has-permissions", args=(user.keycloak_id,)),
            {"permissions": ",".join(permissions)},
        )
        assert response.status_code == 200
        assert response.json()["result"] is True


class UserNoPermissionTestCase(JwtAPITestCase):
    def test_create_user_no_permission(self):
        self.client.force_authenticate(UserFactory())
        response = self.client.post(reverse("ProjectUser-list"))
        assert response.status_code == 403


class UserInvitationTestCase(JwtAPITestCase):
    def test_create_user_with_invitation(self):
        payload = {
            "people_id": faker.uuid4(),
            "email": faker.email(),
            "personal_email": faker.email(),
            "given_name": faker.first_name(),
            "family_name": faker.last_name(),
        }
        invitation = InvitationFactory(
            expire_at=make_aware(datetime.datetime.now() + datetime.timedelta(1))
        )
        self.client.force_authenticate(  # nosec
            token=invitation.token, token_type="Invite"
        )
        response = self.client.post(reverse("ProjectUser-list"), data=payload)
        assert response.status_code == 201
        user = ProjectUser.objects.filter(email=payload["email"])
        assert user.exists()
        user = user.get()
        assert {g.name for g in user.groups.all()} == {
            f"organization:#{invitation.organization.id}:users",
            f"peoplegroup:#{invitation.people_group.id}:members",
        }

    def test_create_user_with_expired_invitation(self):
        payload = {
            "people_id": faker.uuid4(),
            "email": faker.email(),
            "personal_email": faker.email(),
            "given_name": faker.first_name(),
            "family_name": faker.last_name(),
        }
        invitation = InvitationFactory(
            expire_at=make_aware(datetime.datetime.now() - datetime.timedelta(1))
        )
        self.client.force_authenticate(  # nosec
            token=invitation.token, token_type="Invite"
        )
        response = self.client.post(reverse("ProjectUser-list"), data=payload)
        assert response.status_code == 401

    def test_create_user_without_invitation(self):
        payload = {
            "people_id": faker.uuid4(),
            "email": f"{faker.uuid4()}@yopmail.com",
            "personal_email": f"{faker.uuid4()}@yopmail.com",
            "given_name": faker.first_name(),
            "family_name": faker.last_name(),
        }
        response = self.client.post(reverse("ProjectUser-list"), data=payload)
        assert response.status_code == 401


class UserBasePermissionTestCase(JwtAPITestCase):
    def test_create_user_base_permission(self):
        user = UserFactory()
        user.groups.add(get_superadmins_group())
        self.client.force_authenticate(user)
        projects = ProjectFactory.create_batch(3)
        payload = {
            "people_id": faker.uuid4(),
            "email": f"{faker.uuid4()}@yopmail.com",
            "personal_email": f"{faker.uuid4()}@yopmail.com",
            "given_name": faker.first_name(),
            "family_name": faker.last_name(),
            "roles_to_add": [project.get_members().name for project in projects],
        }
        response = self.client.post(reverse("ProjectUser-list"), data=payload)
        assert response.status_code == 201
        content = response.json()
        assert content["people_id"] == payload["people_id"]
        assert content["email"] == payload["email"]
        assert content["given_name"] == payload["given_name"]
        assert content["family_name"] == payload["family_name"]
        assert len(content["roles"]) == 3
        assert {*content["roles"]} == {
            project.get_members().name for project in projects
        }


class UserOrgRolesTestCase(JwtAPITestCase):
    def test_create_user_org_admin(self):
        organization = OrganizationFactory()
        user = UserFactory(groups=[organization.get_admins()])

        self.client.force_authenticate(user)
        payload = {
            "people_id": faker.uuid4(),
            "email": f"{faker.uuid4()}@yopmail.com",
            "personal_email": f"{faker.uuid4()}@yopmail.com",
            "given_name": faker.first_name(),
            "family_name": faker.last_name(),
        }
        response = self.client.post(reverse("ProjectUser-list"), data=payload)
        assert response.status_code == 201
        content = response.json()
        assert content["people_id"] == payload["people_id"]
        assert content["email"] == payload["email"]
        assert content["given_name"] == payload["given_name"]
        assert content["family_name"] == payload["family_name"]

    def test_create_user_org_facilitator(self):
        organization = OrganizationFactory()
        user = UserFactory(groups=[organization.get_facilitators()])

        self.client.force_authenticate(user)
        payload = {
            "people_id": faker.uuid4(),
            "email": f"{faker.uuid4()}@yopmail.com",
            "personal_email": f"{faker.uuid4()}@yopmail.com",
            "given_name": faker.first_name(),
            "family_name": faker.last_name(),
        }
        response = self.client.post(reverse("ProjectUser-list"), data=payload)
        assert response.status_code == 403

    def test_create_user_org_user(self):
        organization = OrganizationFactory()
        user = UserFactory(groups=[organization.get_users()])

        self.client.force_authenticate(user)
        payload = {
            "people_id": faker.uuid4(),
            "email": f"{faker.uuid4()}@yopmail.com",
            "personal_email": f"{faker.uuid4()}@yopmail.com",
            "given_name": faker.first_name(),
            "family_name": faker.last_name(),
        }
        response = self.client.post(reverse("ProjectUser-list"), data=payload)
        assert response.status_code == 403


class UserRolesTestCase(JwtAPITestCase):
    # TODO : django-guardian rework add more tests for that
    def test_update_roles(self):
        project_1 = ProjectFactory()
        project_2 = ProjectFactory()
        people_group_1 = PeopleGroupFactory()
        people_group_2 = PeopleGroupFactory()
        organization_1 = OrganizationFactory()
        organization_2 = OrganizationFactory()
        user = SeedUserFactory()
        user.groups.add(
            get_superadmins_group(),
            project_1.get_members(),
            project_2.get_members(),
            people_group_1.get_members(),
            people_group_2.get_members(),
            organization_1.get_users(),
            organization_2.get_users(),
        )
        self.client.force_authenticate(user)
        payload = {
            "roles_to_add": [
                project_1.get_owners().name,
                people_group_1.get_leaders().name,
                organization_1.get_admins().name,
            ]
        }
        response = self.client.patch(
            reverse("ProjectUser-detail", args=[user.keycloak_id]), data=payload
        )
        assert response.status_code == 200
        assert len(response.data["roles"]) == 8
        assert set(response.data["roles"]) == {
            project_1.get_owners().name,
            project_2.get_members().name,
            people_group_2.get_members().name,
            people_group_1.get_leaders().name,
            organization_1.get_admins().name,
            organization_2.get_users().name,
            get_superadmins_group().name,
            get_default_group().name,
        }


class UserAddedToDefaultTestCase(JwtAPITestCase):
    def test_create_user_with_invitation(self):
        payload = {
            "people_id": faker.uuid4(),
            "email": faker.email(),
            "personal_email": faker.email(),
            "given_name": faker.first_name(),
            "family_name": faker.last_name(),
        }
        invitation = InvitationFactory(
            expire_at=make_aware(datetime.datetime.now() + datetime.timedelta(1))
        )
        self.client.force_authenticate(  # nosec
            token=invitation.token, token_type="Invite"
        )
        response = self.client.post(reverse("ProjectUser-list"), data=payload)
        assert response.status_code == 201
        user = ProjectUser.objects.filter(email=payload["email"])
        assert user.exists()
        user = user.get()
        assert "default" in {g.name for g in user.groups.all()}

    def test_create_user_with_request(self):
        payload = {
            "people_id": faker.uuid4(),
            "email": faker.email(),
            "personal_email": faker.email(),
            "given_name": faker.first_name(),
            "family_name": faker.last_name(),
        }
        self.client.force_authenticate(  # nosec
            UserFactory(groups=[get_superadmins_group()])
        )
        response = self.client.post(reverse("ProjectUser-list"), data=payload)
        assert response.status_code == 201
        user = ProjectUser.objects.filter(email=payload["email"])
        assert user.exists()
        user = user.get()
        assert "default" in {g.name for g in user.groups.all()}
