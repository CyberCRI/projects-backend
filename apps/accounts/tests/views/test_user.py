import datetime

from django.urls import reverse
from django.utils.timezone import make_aware
from faker import Faker
from guardian.shortcuts import assign_perm
from parameterized import parameterized
from rest_framework import status

from apps.accounts.factories import PeopleGroupFactory, SeedUserFactory, UserFactory
from apps.accounts.models import ProjectUser
from apps.accounts.utils import get_default_group, get_superadmins_group
from apps.commons.test import JwtAPITestCase, TestRoles
from apps.invitations.factories import InvitationFactory
from apps.notifications.factories import NotificationFactory
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory

faker = Faker()


class CreateUserTestCase(JwtAPITestCase):
    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_201_CREATED),
            (TestRoles.ORG_ADMIN, status.HTTP_201_CREATED),
            (TestRoles.ORG_FACILITATOR, status.HTTP_403_FORBIDDEN),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_create_user(self, role, expected_code):
        organization = OrganizationFactory()
        user = self.get_parameterized_test_user(role, organization=organization)
        self.client.force_authenticate(user)
        projects = ProjectFactory.create_batch(3, organizations=[organization])
        people_groups = PeopleGroupFactory.create_batch(3, organization=organization)
        payload = {
            "people_id": faker.uuid4(),
            "email": f"{faker.uuid4()}@yopmail.com",
            "personal_email": f"{faker.uuid4()}@yopmail.com",
            "given_name": faker.first_name(),
            "family_name": faker.last_name(),
            "roles_to_add": [
                organization.get_users().name,
                *[project.get_members().name for project in projects],
                *[people_group.get_members().name for people_group in people_groups],
            ],
        }
        response = self.client.post(reverse("ProjectUser-list"), data=payload)
        assert response.status_code == expected_code
        if expected_code == status.HTTP_201_CREATED:
            content = response.json()
            assert content["people_id"] == payload["people_id"]
            assert content["email"] == payload["email"]
            assert content["given_name"] == payload["given_name"]
            assert content["family_name"] == payload["family_name"]
            assert len(content["roles"]) == 8
            assert {*content["roles"]} == {
                get_default_group().name,
                organization.get_users().name,
                *[project.get_members().name for project in projects],
                *[people_group.get_members().name for people_group in people_groups],
            }

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
            get_default_group().name,
            invitation.organization.get_users().name,
            invitation.people_group.get_members().name,
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


class UpdateUserTestCase(JwtAPITestCase):
    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.OWNER, status.HTTP_200_OK),
            (TestRoles.SUPERADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_ADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_FACILITATOR, status.HTTP_200_OK),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_update_user(self, role, expected_code):
        organization = OrganizationFactory()
        instance = SeedUserFactory(groups=[organization.get_users()])
        user = self.get_parameterized_test_user(
            role, organization=organization, owned_instance=instance
        )
        self.client.force_authenticate(user)
        payload = {
            "pronouns": "She / Her",
            "sdgs": [1, 2, 3],
        }
        response = self.client.patch(
            reverse("ProjectUser-detail", args=(instance.keycloak_id,)),
            payload,
        )
        assert response.status_code == expected_code
        if expected_code == status.HTTP_200_OK:
            assert response.json()["pronouns"] == payload["pronouns"]
            assert response.json()["sdgs"] == payload["sdgs"]


class DeleteUserTestCase(JwtAPITestCase):
    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.OWNER, status.HTTP_204_NO_CONTENT),
            (TestRoles.SUPERADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_ADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_FACILITATOR, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_delete_user(self, role, expected_code):
        organization = OrganizationFactory()
        instance = SeedUserFactory(groups=[organization.get_users()])
        user = self.get_parameterized_test_user(
            role, organization=organization, owned_instance=instance
        )
        self.client.force_authenticate(user)
        response = self.client.delete(
            reverse("ProjectUser-detail", args=(instance.keycloak_id,))
        )
        assert response.status_code == expected_code
        if expected_code == status.HTTP_204_NO_CONTENT:
            assert not ProjectUser.objects.filter(pk=instance.pk).exists()


class FilterSearchOrderUserTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        # Overwrite this method because it creates a user and makes some tests fail
        pass

    def test_order_by_job(self):
        user_a = UserFactory(job="A")
        user_b = UserFactory(job="B")
        user_c = UserFactory(job="C")
        response = self.client.get(reverse("ProjectUser-list") + "?ordering=job")
        assert response.status_code == 200
        assert response.data["results"][0]["keycloak_id"] == user_a.keycloak_id
        assert response.data["results"][1]["keycloak_id"] == user_b.keycloak_id
        assert response.data["results"][2]["keycloak_id"] == user_c.keycloak_id
        response = self.client.get(reverse("ProjectUser-list") + "?ordering=-job")
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
            reverse("ProjectUser-list")
            + f"?ordering=current_org_role&current_org_pk={organization.pk}"
        )
        assert response.status_code == 200
        assert response.data["results"][0]["keycloak_id"] == user_a.keycloak_id
        assert response.data["results"][1]["keycloak_id"] == user_b.keycloak_id
        assert response.data["results"][2]["keycloak_id"] == user_c.keycloak_id
        assert response.data["results"][3]["keycloak_id"] == user_d.keycloak_id
        response = self.client.get(
            reverse("ProjectUser-list")
            + f"?ordering=-current_org_role&current_org_pk={organization.pk}"
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
            reverse("ProjectUser-list")
            + f"?current_org_role=admins&current_org_pk={organization.pk}"
        )
        assert response.status_code == 200
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["keycloak_id"] == user_a.keycloak_id
        response = self.client.get(
            reverse("ProjectUser-list")
            + f"?current_org_role=facilitators&current_org_pk={organization.pk}"
        )
        assert response.status_code == 200
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["keycloak_id"] == user_b.keycloak_id
        response = self.client.get(
            reverse("ProjectUser-list")
            + f"?current_org_role=users&current_org_pk={organization.pk}"
        )
        assert response.status_code == 200
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["keycloak_id"] == user_c.keycloak_id
        response = self.client.get(
            reverse("ProjectUser-list")
            + f"?current_org_role=_no_role&current_org_pk={organization.pk}"
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
        response = self.client.get(reverse("ProjectUser-list") + "?search=ABCDE")
        assert response.status_code == 200
        assert response.data["results"][0]["keycloak_id"] == user_a.keycloak_id
        response = self.client.get(reverse("ProjectUser-list") + "?search=VWXYZ")
        assert response.status_code == 200
        assert response.data["results"][0]["keycloak_id"] == user_b.keycloak_id
        response = self.client.get(reverse("ProjectUser-list") + "?search=FGHIJ")
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
        response = self.client.get(reverse("ProjectUser-list") + "?search=ABCDE")
        assert response.status_code == 200
        assert response.data["results"][0]["keycloak_id"] == user_a.keycloak_id
        response = self.client.get(reverse("ProjectUser-list") + "?search=VWXYZ")
        assert response.status_code == 200
        assert response.data["results"][0]["keycloak_id"] == user_b.keycloak_id
        response = self.client.get(reverse("ProjectUser-list") + "?search=FGHIJ")
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
            reverse("ProjectUser-list")
            + f"?search=ABCDE&current_org_pk={organization.pk}"
        )
        assert response.status_code == 200
        assert response.data["results"][0]["keycloak_id"] == user_a.keycloak_id
        response = self.client.get(
            reverse("ProjectUser-list")
            + f"?search=VWXYZ&current_org_pk={organization.pk}"
        )
        assert response.status_code == 200
        assert response.data["results"][0]["keycloak_id"] == user_b.keycloak_id
        response = self.client.get(
            reverse("ProjectUser-list")
            + f"?search=FGHIJ&current_org_pk={organization.pk}"
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


class MiscUserTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        # Overwrite this method because it creates a user and makes some tests fail
        pass

    def test_notifications_count(self):
        user = UserFactory()
        NotificationFactory.create_batch(5, receiver=user, is_viewed=False)
        NotificationFactory(receiver=user, is_viewed=True)
        NotificationFactory()
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("ProjectUser-detail", args=(user.keycloak_id,))
        )
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

    def test_check_permissions(self):
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
