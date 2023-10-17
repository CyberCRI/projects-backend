import datetime
from unittest import mock

from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart
from django.urls import reverse
from django.utils.timezone import make_aware
from faker import Faker
from googleapiclient.errors import HttpError
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
from keycloak import KeycloakDeleteError

faker = Faker()


class CreateUserTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.projects = ProjectFactory.create_batch(3, organizations=[cls.organization])
        cls.people_groups = PeopleGroupFactory.create_batch(
            3, organization=cls.organization
        )

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
        organization = self.organization
        projects = self.projects
        people_groups = self.people_groups
        user = self.get_parameterized_test_user(role, organization=organization)
        self.client.force_authenticate(user)
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
            keycloak_user = KeycloakService().get_user(content["keycloak_id"])
            assert keycloak_user is not None
            assert set(keycloak_user["requiredActions"]) == {
                "VERIFY_EMAIL",
                "UPDATE_PASSWORD",
            }

    def test_create_user_with_formdata(self):
        organization = self.organization
        projects = self.projects
        people_groups = self.people_groups
        user = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(user)
        payload = {
            "people_id": faker.uuid4(),
            "email": f"{faker.uuid4()}@yopmail.com",
            "personal_email": f"{faker.uuid4()}@yopmail.com",
            "given_name": faker.first_name(),
            "family_name": faker.last_name(),
            "sdgs": [1],
            "profile_picture_scale_x": 2.0,
            "profile_picture_scale_y": 2.0,
            "profile_picture_left": 1.0,
            "profile_picture_top": 1.0,
            "profile_picture_natural_ratio": 1.0,
            "profile_picture_file": self.get_test_image_file(),
            "roles_to_add": [
                organization.get_users().name,
                *[project.get_members().name for project in projects],
                *[people_group.get_members().name for people_group in people_groups],
            ],
        }
        response = self.client.post(
            reverse("ProjectUser-list"),
            data=encode_multipart(data=payload, boundary=BOUNDARY),
            content_type=MULTIPART_CONTENT,
        )
        assert response.status_code == status.HTTP_201_CREATED
        content = response.json()
        assert content["people_id"] == payload["people_id"]
        assert content["email"] == payload["email"]
        assert content["given_name"] == payload["given_name"]
        assert content["family_name"] == payload["family_name"]
        assert content["sdgs"] == payload["sdgs"]
        assert content["profile_picture"] is not None
        assert (
            content["profile_picture"]["scale_x"] == payload["profile_picture_scale_x"]
        )
        assert (
            content["profile_picture"]["scale_y"] == payload["profile_picture_scale_y"]
        )
        assert content["profile_picture"]["left"] == payload["profile_picture_left"]
        assert content["profile_picture"]["top"] == payload["profile_picture_top"]
        assert (
            content["profile_picture"]["natural_ratio"]
            == payload["profile_picture_natural_ratio"]
        )
        assert len(content["roles"]) == 8
        assert {*content["roles"]} == {
            get_default_group().name,
            organization.get_users().name,
            *[project.get_members().name for project in projects],
            *[people_group.get_members().name for people_group in people_groups],
        }
        keycloak_user = KeycloakService().get_user(content["keycloak_id"])
        assert keycloak_user is not None
        assert set(keycloak_user["requiredActions"]) == {
            "VERIFY_EMAIL",
            "UPDATE_PASSWORD",
        }

    def test_create_user_with_invitation(self):
        organization = self.organization
        people_group = PeopleGroupFactory(organization=self.organization)
        payload = {
            "people_id": faker.uuid4(),
            "email": faker.email(),
            "personal_email": faker.email(),
            "given_name": faker.first_name(),
            "family_name": faker.last_name(),
            "password": faker.password(),
        }
        invitation = InvitationFactory(
            expire_at=make_aware(datetime.datetime.now() + datetime.timedelta(1)),
            organization=organization,
            people_group=people_group,
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
            organization.get_users().name,
            people_group.get_members().name,
        }
        keycloak_user = KeycloakService().get_user(user.keycloak_id)
        assert keycloak_user is not None
        assert keycloak_user["requiredActions"] == ["VERIFY_EMAIL"]

    def test_create_user_with_expired_invitation(self):
        organization = self.organization
        people_group = PeopleGroupFactory(organization=self.organization)
        payload = {
            "people_id": faker.uuid4(),
            "email": faker.email(),
            "personal_email": faker.email(),
            "given_name": faker.first_name(),
            "family_name": faker.last_name(),
        }
        invitation = InvitationFactory(
            expire_at=make_aware(datetime.datetime.now() - datetime.timedelta(1)),
            organization=organization,
            people_group=people_group,
        )
        self.client.force_authenticate(  # nosec
            token=invitation.token, token_type="Invite"
        )
        response = self.client.post(reverse("ProjectUser-list"), data=payload)
        assert response.status_code == 401


class UpdateUserTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()

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
        organization = self.organization
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
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()

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
        organization = self.organization
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


class UserSyncErrorsTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory(code="TEST_GOOGLE_SYNC")

    @staticmethod
    def mocked_google_error(code=400):
        def raise_error(*args, **kwargs):
            raise HttpError(
                resp=mock.Mock(status=code, reason="error reason"),
                content=b'{"error": {"errors": [{"reason": "error reason"}]}}',
            )

        return raise_error

    @staticmethod
    def mocked_keycloak_error(*args, **kwarg):
        raise KeycloakDeleteError(
            "error reason", 400, response_body=b'{"errorMessage": "error reason"}'
        )

    def test_keycloak_error_create_user(self):
        self.client.force_authenticate(UserFactory(groups=[get_superadmins_group()]))
        user = SeedUserFactory()
        payload = {
            "people_id": faker.uuid4(),
            "email": user.email,
            "personal_email": f"{faker.uuid4()}@yopmail.com",
            "given_name": faker.first_name(),
            "family_name": faker.last_name(),
        }
        response = self.client.post(reverse("ProjectUser-list"), data=payload)
        assert response.status_code == 409
        assert (
            response.json()["error"]
            == "An error occured in Keycloak : User exists with same username"
        )
        assert not ProjectUser.objects.filter(people_id=payload["people_id"]).exists()

    def test_keycloak_error_update_user(self):
        self.client.force_authenticate(UserFactory(groups=[get_superadmins_group()]))
        user = SeedUserFactory()
        user_2 = SeedUserFactory()
        payload = {
            "email": user_2.email,
        }
        response = self.client.patch(
            reverse("ProjectUser-detail", args=[user.keycloak_id]), data=payload
        )
        assert response.status_code == 409
        assert (
            response.json()["error"]
            == "An error occured in Keycloak : User exists with same username or email"
        )
        assert (
            ProjectUser.objects.get(keycloak_id=user.keycloak_id).email != user_2.email
        )

    @mock.patch("services.keycloak.interface.KeycloakService.delete_user")
    def test_keycloak_error_delete_user(self, mocked):
        mocked.side_effect = self.mocked_keycloak_error
        self.client.force_authenticate(UserFactory(groups=[get_superadmins_group()]))
        user = UserFactory()
        response = self.client.delete(
            reverse("ProjectUser-detail", args=[user.keycloak_id])
        )
        assert response.status_code == 400
        assert response.json()["error"] == "An error occured in Keycloak : error reason"
        assert ProjectUser.objects.filter(keycloak_id=user.keycloak_id).exists()

    def test_keycloak_404_delete_user(self):
        self.client.force_authenticate(UserFactory(groups=[get_superadmins_group()]))
        user = UserFactory()
        response = self.client.delete(
            reverse("ProjectUser-detail", args=[user.keycloak_id])
        )
        assert response.status_code == 204
        assert not ProjectUser.objects.filter(keycloak_id=user.keycloak_id).exists()


class ValidateUserTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()

    def test_create_user_group_validation_no_permission(self):
        organization = self.organization
        organization_2 = OrganizationFactory()
        self.client.force_authenticate(UserFactory(groups=[organization.get_admins()]))
        payload = {
            "people_id": faker.uuid4(),
            "email": f"{faker.uuid4()}@yopmail.com",
            "personal_email": f"{faker.uuid4()}@yopmail.com",
            "given_name": faker.first_name(),
            "family_name": faker.last_name(),
            "roles_to_add": [
                organization.get_users().name,
                organization_2.get_users().name,
            ],
        }
        response = self.client.post(reverse("ProjectUser-list"), data=payload)
        assert response.status_code == 403
        assert f"organization:#{organization_2.pk}:users" in response.json()["detail"]


class FilterSearchOrderUserTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        ProjectUser.objects.all().delete()
        params = {
            "given_name": "test",
            "family_name": "test",
            "email": "test@test.com",
        }
        cls.user_a = UserFactory(job="ABC", **params)
        cls.user_b = UserFactory(job="DEF", **params)
        cls.user_c = UserFactory(job="GHI", **params)
        cls.user_d = UserFactory(job="JKL", **params)
        cls.people_group_a = PeopleGroupFactory(name="MNO")
        cls.people_group_b = PeopleGroupFactory(name="PQR")
        cls.people_group_c = PeopleGroupFactory(name="STU")
        cls.people_group_d = PeopleGroupFactory(name="VWX")
        cls.people_group_a.members.add(cls.user_a)
        cls.people_group_b.members.add(cls.user_b)
        cls.people_group_c.members.add(cls.user_c)
        cls.people_group_d.members.add(cls.user_d)
        cls.organization.admins.add(cls.user_a)
        cls.organization.facilitators.add(cls.user_b)
        cls.organization.users.add(cls.user_c)

    def test_order_by_job(self):
        response = self.client.get(reverse("ProjectUser-list") + "?ordering=job")
        assert response.status_code == 200
        assert response.data["results"][0]["keycloak_id"] == self.user_a.keycloak_id
        assert response.data["results"][1]["keycloak_id"] == self.user_b.keycloak_id
        assert response.data["results"][2]["keycloak_id"] == self.user_c.keycloak_id
        assert response.data["results"][3]["keycloak_id"] == self.user_d.keycloak_id
        response = self.client.get(reverse("ProjectUser-list") + "?ordering=-job")
        assert response.status_code == 200
        assert response.data["results"][0]["keycloak_id"] == self.user_d.keycloak_id
        assert response.data["results"][1]["keycloak_id"] == self.user_c.keycloak_id
        assert response.data["results"][2]["keycloak_id"] == self.user_b.keycloak_id
        assert response.data["results"][3]["keycloak_id"] == self.user_a.keycloak_id

    def test_order_by_role(self):
        response = self.client.get(
            reverse("ProjectUser-list")
            + f"?ordering=current_org_role&current_org_pk={self.organization.pk}"
        )
        assert response.status_code == 200
        assert response.data["results"][0]["keycloak_id"] == self.user_a.keycloak_id
        assert response.data["results"][1]["keycloak_id"] == self.user_b.keycloak_id
        assert response.data["results"][2]["keycloak_id"] == self.user_c.keycloak_id
        assert response.data["results"][3]["keycloak_id"] == self.user_d.keycloak_id
        response = self.client.get(
            reverse("ProjectUser-list")
            + f"?ordering=-current_org_role&current_org_pk={self.organization.pk}"
        )
        assert response.status_code == 200
        assert response.data["results"][0]["keycloak_id"] == self.user_d.keycloak_id
        assert response.data["results"][1]["keycloak_id"] == self.user_c.keycloak_id
        assert response.data["results"][2]["keycloak_id"] == self.user_b.keycloak_id
        assert response.data["results"][3]["keycloak_id"] == self.user_a.keycloak_id

    def filter_by_role(self):
        response = self.client.get(
            reverse("ProjectUser-list")
            + f"?current_org_role=admins&current_org_pk={self.organization.pk}"
        )
        assert response.status_code == 200
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["keycloak_id"] == self.user_a.keycloak_id
        response = self.client.get(
            reverse("ProjectUser-list")
            + f"?current_org_role=facilitators&current_org_pk={self.organization.pk}"
        )
        assert response.status_code == 200
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["keycloak_id"] == self.user_b.keycloak_id
        response = self.client.get(
            reverse("ProjectUser-list")
            + f"?current_org_role=users&current_org_pk={self.organization.pk}"
        )
        assert response.status_code == 200
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["keycloak_id"] == self.user_c.keycloak_id
        response = self.client.get(
            reverse("ProjectUser-list")
            + f"?current_org_role=_no_role&current_org_pk={self.organization.pk}"
        )
        assert response.status_code == 200
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["keycloak_id"] == self.user_d.keycloak_id

    def test_search_by_job(self):
        response = self.client.get(reverse("ProjectUser-list") + "?search=ABC")
        assert response.status_code == 200
        assert response.data["results"][0]["keycloak_id"] == self.user_a.keycloak_id
        response = self.client.get(reverse("ProjectUser-list") + "?search=DEF")
        assert response.status_code == 200
        assert response.data["results"][0]["keycloak_id"] == self.user_b.keycloak_id
        response = self.client.get(reverse("ProjectUser-list") + "?search=GHI")
        assert response.status_code == 200
        assert response.data["results"][0]["keycloak_id"] == self.user_c.keycloak_id

    def test_search_by_people_group(self):
        response = self.client.get(reverse("ProjectUser-list") + "?search=MNO")
        assert response.status_code == 200
        assert response.data["results"][0]["keycloak_id"] == self.user_a.keycloak_id
        response = self.client.get(reverse("ProjectUser-list") + "?search=PQR")
        assert response.status_code == 200
        assert response.data["results"][0]["keycloak_id"] == self.user_b.keycloak_id
        response = self.client.get(reverse("ProjectUser-list") + "?search=STU")
        assert response.status_code == 200
        assert response.data["results"][0]["keycloak_id"] == self.user_c.keycloak_id

    def test_search_with_current_org_pk(self):
        response = self.client.get(
            reverse("ProjectUser-list")
            + f"?search=ABC&current_org_pk={self.organization.pk}"
        )
        assert response.status_code == 200
        assert response.data["results"][0]["keycloak_id"] == self.user_a.keycloak_id
        response = self.client.get(
            reverse("ProjectUser-list")
            + f"?search=DEF&current_org_pk={self.organization.pk}"
        )
        assert response.status_code == 200
        assert response.data["results"][0]["keycloak_id"] == self.user_b.keycloak_id
        response = self.client.get(
            reverse("ProjectUser-list")
            + f"?search=GHI&current_org_pk={self.organization.pk}"
        )
        assert response.status_code == 200
        assert response.data["results"][0]["keycloak_id"] == self.user_c.keycloak_id


class MiscUserTestCase(JwtAPITestCase):
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
        keycloak_user = KeycloakService().get_user(response.data["keycloak_id"])
        assert keycloak_user["attributes"]["locale"] == ["fr"]

    def test_language_from_payload(self):
        user = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(user)
        organization = OrganizationFactory(language="en")
        payload = {
            "people_id": faker.uuid4(),
            "email": f"{faker.uuid4()}@yopmail.com",
            "personal_email": f"{faker.uuid4()}@yopmail.com",
            "given_name": faker.first_name(),
            "family_name": faker.last_name(),
            "roles_to_add": [organization.get_users().name],
            "language": "fr",
        }
        response = self.client.post(reverse("ProjectUser-list"), data=payload)
        assert response.status_code == 201
        assert response.data["language"] == "fr"
        keycloak_user = KeycloakService().get_user(response.data["keycloak_id"])
        assert keycloak_user["attributes"]["locale"] == ["fr"]

    def test_keycloak_attributes_updated(self):
        self.client.force_authenticate(UserFactory(groups=[get_superadmins_group()]))
        user = SeedUserFactory(language="en")
        KeycloakService.service().update_user(
            user.keycloak_id,
            {"attributes": {"attribute_1": ["value_1"], "locale": ["en"]}},
        )
        payload = {
            "language": "fr",
        }
        response = self.client.patch(
            reverse("ProjectUser-detail", args=[user.keycloak_id]), data=payload
        )
        assert response.status_code == 200
        assert response.data["language"] == "fr"
        keycloak_user = KeycloakService().get_user(user.keycloak_id)
        assert keycloak_user["attributes"]["attribute_1"] == ["value_1"]
        assert keycloak_user["attributes"]["locale"] == ["fr"]

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
