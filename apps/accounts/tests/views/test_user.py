import datetime
import random
from unittest.mock import Mock, patch

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
from apps.misc.models import SDG
from apps.notifications.factories import NotificationFactory
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory
from keycloak import KeycloakDeleteError
from services.keycloak.interface import KeycloakService
from services.keycloak.models import KeycloakAccount

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
    @patch("services.keycloak.interface.KeycloakService.send_email")
    def test_create_user(self, role, expected_code, mocked):
        mocked.return_value = {}
        organization = self.organization
        projects = self.projects
        people_groups = self.people_groups
        user = self.get_parameterized_test_user(role, instances=[organization])
        self.client.force_authenticate(user)
        payload = {
            "email": f"{faker.uuid4()}@{faker.domain_name()}",
            "given_name": faker.first_name(),
            "family_name": faker.last_name(),
            "roles_to_add": [
                organization.get_users().name,
                *[project.get_members().name for project in projects],
                *[people_group.get_members().name for people_group in people_groups],
            ],
        }
        response = self.client.post(
            reverse("ProjectUser-list") + f"?organization={organization.code}",
            data=payload,
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_201_CREATED:
            content = response.json()
            self.assertTrue(content["onboarding_status"]["show_welcome"])
            self.assertEqual(content["email"], payload["email"])
            self.assertEqual(content["given_name"], payload["given_name"])
            self.assertEqual(content["family_name"], payload["family_name"])
            self.assertEqual(len(content["roles"]), 8)
            self.assertSetEqual(
                {*content["roles"]},
                {
                    get_default_group().name,
                    organization.get_users().name,
                    *[project.get_members().name for project in projects],
                    *[
                        people_group.get_members().name
                        for people_group in people_groups
                    ],
                },
            )
            keycloak_user = KeycloakService.get_user(content["keycloak_id"])
            self.assertIsNotNone(keycloak_user)
            self.assertSetEqual(
                set(keycloak_user["requiredActions"]),
                {"VERIFY_EMAIL", "UPDATE_PASSWORD"},
            )

    @patch("services.keycloak.interface.KeycloakService.send_email")
    def test_create_user_with_formdata(self, mocked):
        mocked.return_value = {}
        organization = self.organization
        projects = self.projects
        people_groups = self.people_groups
        user = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(user)
        payload = {
            "email": f"{faker.uuid4()}@{faker.domain_name()}",
            "given_name": faker.first_name(),
            "family_name": faker.last_name(),
            "sdgs": random.choices(SDG.values, k=3),  # nosec
            "profile_picture_scale_x": faker.pyfloat(min_value=1.0, max_value=2.0),
            "profile_picture_scale_y": faker.pyfloat(min_value=1.0, max_value=2.0),
            "profile_picture_left": faker.pyfloat(min_value=1.0, max_value=2.0),
            "profile_picture_top": faker.pyfloat(min_value=1.0, max_value=2.0),
            "profile_picture_natural_ratio": faker.pyfloat(
                min_value=1.0, max_value=2.0
            ),
            "profile_picture_file": self.get_test_image_file(),
            "roles_to_add": [
                organization.get_users().name,
                *[project.get_members().name for project in projects],
                *[people_group.get_members().name for people_group in people_groups],
            ],
        }
        response = self.client.post(
            reverse("ProjectUser-list") + f"?organization={organization.code}",
            data=encode_multipart(data=payload, boundary=BOUNDARY),
            content_type=MULTIPART_CONTENT,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        content = response.json()
        self.assertTrue(content["onboarding_status"]["show_welcome"])
        self.assertEqual(content["email"], payload["email"])
        self.assertEqual(content["given_name"], payload["given_name"])
        self.assertEqual(content["family_name"], payload["family_name"])
        self.assertEqual(content["sdgs"], payload["sdgs"])
        self.assertIsNotNone(content["profile_picture"])
        self.assertEqual(
            content["profile_picture"]["scale_x"], payload["profile_picture_scale_x"]
        )
        self.assertEqual(
            content["profile_picture"]["scale_y"], payload["profile_picture_scale_y"]
        )
        self.assertEqual(
            content["profile_picture"]["left"], payload["profile_picture_left"]
        )
        self.assertEqual(
            content["profile_picture"]["top"], payload["profile_picture_top"]
        )
        self.assertEqual(
            content["profile_picture"]["natural_ratio"],
            payload["profile_picture_natural_ratio"],
        )
        self.assertEqual(len(content["roles"]), 8)
        self.assertSetEqual(
            {*content["roles"]},
            {
                get_default_group().name,
                organization.get_users().name,
                *[project.get_members().name for project in projects],
                *[people_group.get_members().name for people_group in people_groups],
            },
        )
        keycloak_user = KeycloakService.get_user(content["keycloak_id"])
        self.assertIsNotNone(keycloak_user)
        self.assertSetEqual(
            set(keycloak_user["requiredActions"]),
            {"VERIFY_EMAIL", "UPDATE_PASSWORD"},
        )

    @patch("services.keycloak.interface.KeycloakService.send_email")
    def test_create_user_with_invitation(self, mocked):
        mocked.return_value = {}
        organization = self.organization
        people_group = PeopleGroupFactory(organization=self.organization)
        payload = {
            "email": f"{faker.uuid4()}@{faker.domain_name()}",
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
        response = self.client.post(
            reverse("ProjectUser-list") + f"?organization={organization.code}",
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = ProjectUser.objects.filter(email=payload["email"])
        self.assertTrue(user.exists())
        user = user.get()
        self.assertTrue(user.onboarding_status["show_welcome"])
        self.assertSetEqual(
            {g.name for g in user.groups.all()},
            {
                get_default_group().name,
                organization.get_users().name,
                people_group.get_members().name,
            },
        )
        keycloak_user = KeycloakService.get_user(user.keycloak_id)
        self.assertIsNotNone(keycloak_user)
        self.assertListEqual(keycloak_user["requiredActions"], ["VERIFY_EMAIL"])

    @patch("services.keycloak.interface.KeycloakService.send_email")
    def test_create_user_with_expired_invitation(self, mocked):
        mocked.return_value = {}
        organization = self.organization
        people_group = PeopleGroupFactory(organization=self.organization)
        payload = {
            "email": f"{faker.uuid4()}@{faker.domain_name()}",
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
        response = self.client.post(
            reverse("ProjectUser-list") + f"?organization={organization.code}",
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class UpdateUserTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.instance = SeedUserFactory(groups=[cls.organization.get_users()])

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
        user = self.get_parameterized_test_user(
            role, instances=[self.organization], owned_instance=self.instance
        )
        self.client.force_authenticate(user)
        payload = {
            "pronouns": faker.word(),
            "sdgs": random.choices(SDG.values, k=3),  # nosec
        }
        response = self.client.patch(
            reverse("ProjectUser-detail", args=(self.instance.id,)),
            payload,
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_200_OK:
            content = response.json()
            self.assertEqual(content["pronouns"], payload["pronouns"])
            self.assertEqual(content["sdgs"], payload["sdgs"])


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
            role, instances=[organization], owned_instance=instance
        )
        self.client.force_authenticate(user)
        response = self.client.delete(
            reverse("ProjectUser-detail", args=(instance.id,))
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_204_NO_CONTENT:
            self.assertFalse(ProjectUser.objects.filter(id=instance.id).exists())


class AdminListUserTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.user = UserFactory(groups=[get_superadmins_group()])
        cls.user_1 = SeedUserFactory(groups=[cls.organization.get_admins()])
        KeycloakService._update_user(
            str(cls.user_1.keycloak_id),
            {
                "username": cls.user_1.email,
                "email": cls.user_1.email,
                "firstName": cls.user_1.given_name,
                "lastName": cls.user_1.family_name,
                "emailVerified": True,
                "requiredActions": [],
            },
        )
        cls.user_2 = SeedUserFactory(groups=[cls.organization.get_facilitators()])
        KeycloakService._update_user(
            str(cls.user_2.keycloak_id),
            {
                "username": cls.user_2.email,
                "email": cls.user_2.email,
                "firstName": cls.user_2.given_name,
                "lastName": cls.user_2.family_name,
                "emailVerified": False,
                "requiredActions": [],
            },
        )
        cls.user_3 = UserFactory(groups=[cls.organization.get_users()])
        KeycloakAccount.objects.get(user=cls.user_3).delete()
        cls.user_4 = UserFactory()
        cls.users = [
            {"user": cls.user_1, "email_verified": True},
            {"user": cls.user_2, "email_verified": False},
            {"user": cls.user_3, "email_verified": False},
        ]

    def test_list_accounts_status(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(
            reverse("ProjectUser-admin-list")
            + f"?organizations={self.organization.code}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), len(self.users))
        content = {user["id"]: user for user in response.data["results"]}
        for user in self.users:
            self.assertEqual(
                content[user["user"].id]["email_verified"], user["email_verified"]
            )

    def test_order_by_email_verified(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(
            reverse("ProjectUser-admin-list")
            + f"?ordering=email_verified&organizations={self.organization.code}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertSetEqual(
            {u["id"] for u in response.data["results"][:2]},
            {self.user_2.id, self.user_3.id},
        )
        self.assertSetEqual(
            {u["id"] for u in response.data["results"][2:]},
            {self.user_1.id},
        )

    def test_order_by_email_verified_reverse(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(
            reverse("ProjectUser-admin-list")
            + f"?ordering=-email_verified&organizations={self.organization.code}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertSetEqual(
            {u["id"] for u in response.data["results"][:1]},
            {self.user_1.id},
        )
        self.assertSetEqual(
            {u["id"] for u in response.data["results"][1:]},
            {self.user_2.id, self.user_3.id},
        )

    def test_order_by_created_at(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(
            reverse("ProjectUser-admin-list")
            + f"?ordering=created_at&organizations={self.organization.code}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertListEqual(
            [u["id"] for u in response.data["results"]],
            [self.user_1.id, self.user_2.id, self.user_3.id],
        )

    def test_order_by_created_at_reverse(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(
            reverse("ProjectUser-admin-list")
            + f"?ordering=-created_at&organizations={self.organization.code}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertListEqual(
            [u["id"] for u in response.data["results"]],
            [self.user_3.id, self.user_2.id, self.user_1.id],
        )

    def test_order_by_role(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(
            reverse("ProjectUser-admin-list")
            + "?ordering=current_org_role"
            + f"&organizations={self.organization.code}"
            + f"&current_org_pk={self.organization.pk}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertListEqual(
            [u["id"] for u in response.data["results"]],
            [self.user_1.id, self.user_2.id, self.user_3.id],
        )

    def test_order_by_role_reverse(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(
            reverse("ProjectUser-admin-list")
            + "?ordering=-current_org_role"
            + f"&organizations={self.organization.code}"
            + f"&current_org_pk={self.organization.pk}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertListEqual(
            [u["id"] for u in response.data["results"]],
            [self.user_3.id, self.user_2.id, self.user_1.id],
        )

    def test_filter_by_role_admin(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(
            reverse("ProjectUser-admin-list")
            + f"?current_org_role=admins&current_org_pk={self.organization.pk}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(len(content["results"]), 1)
        self.assertEqual(content["results"][0]["id"], self.user_1.id)

    def test_filter_by_role_facilitator(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(
            reverse("ProjectUser-admin-list")
            + f"?current_org_role=facilitators&current_org_pk={self.organization.pk}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(len(content["results"]), 1)
        self.assertEqual(content["results"][0]["id"], self.user_2.id)

    def test_filter_by_role_user(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(
            reverse("ProjectUser-admin-list")
            + f"?current_org_role=users&current_org_pk={self.organization.pk}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(len(content["results"]), 1)
        self.assertEqual(content["results"][0]["id"], self.user_3.id)

    def test_filter_by_multiple_roles(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(
            reverse("ProjectUser-admin-list")
            + f"?current_org_role=admins,users&current_org_pk={self.organization.pk}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(len(content["results"]), 2)
        self.assertSetEqual(
            {u["id"] for u in content["results"]},
            {self.user_1.id, self.user_3.id},
        )

    def test_filter_by_organization(self):
        self.client.force_authenticate(self.user)
        other_organization = OrganizationFactory(parent=self.organization)
        other_organization.admins.add(self.user_4)
        response = self.client.get(
            reverse("ProjectUser-admin-list")
            + f"?organizations={self.organization.code}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(len(content["results"]), 3)
        self.assertSetEqual(
            {u["id"] for u in content["results"]},
            {self.user_1.id, self.user_2.id, self.user_3.id},
        )


class UserSyncErrorsTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory(code="TEST_GOOGLE_SYNC")

    @staticmethod
    def mocked_google_error(code=400):
        def raise_error(*args, **kwargs):
            raise HttpError(
                resp=Mock(status=code, reason="error reason"),
                content=b'{"error": {"errors": [{"reason": "error reason"}]}}',
            )

        return raise_error

    @staticmethod
    def mocked_keycloak_error(*args, **kwarg):
        raise KeycloakDeleteError(
            "error reason", 400, response_body=b'{"errorMessage": "error reason"}'
        )

    @patch("services.keycloak.interface.KeycloakService.send_email")
    def test_keycloak_error_create_user(self, mocked):
        mocked.return_value = {}
        self.client.force_authenticate(UserFactory(groups=[get_superadmins_group()]))
        existing_username = f"{faker.uuid4()}@{faker.domain_name()}"
        KeycloakService._create_user(
            {
                "username": existing_username,
                "email": existing_username,
                "firstName": faker.first_name(),
                "lastName": faker.last_name(),
            }
        )
        payload = {
            "email": existing_username,
            "given_name": faker.first_name(),
            "family_name": faker.last_name(),
        }
        response = self.client.post(
            reverse("ProjectUser-list") + f"?organization={self.organization.code}",
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertApiTechnicalError(
            response,
            "An error occurred while syncing with Keycloak : User exists with same email",
        )
        self.assertFalse(ProjectUser.objects.filter(**payload).exists())

    def test_keycloak_error_update_user(self):
        self.client.force_authenticate(UserFactory(groups=[get_superadmins_group()]))
        existing_username = f"{faker.uuid4()}@{faker.domain_name()}"
        KeycloakService._create_user(
            {
                "username": existing_username,
                "email": existing_username,
                "firstName": faker.first_name(),
                "lastName": faker.last_name(),
            }
        )
        user = SeedUserFactory()
        payload = {
            "email": existing_username,
        }
        response = self.client.patch(
            reverse("ProjectUser-detail", args=(user.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertApiTechnicalError(
            response,
            "An error occurred while syncing with Keycloak : User exists with same email",
        )
        self.assertNotEqual(
            ProjectUser.objects.get(id=user.id).email, existing_username
        )

    @patch("services.keycloak.interface.KeycloakService.delete_user")
    def test_keycloak_error_delete_user(self, mocked):
        mocked.side_effect = self.mocked_keycloak_error
        self.client.force_authenticate(UserFactory(groups=[get_superadmins_group()]))
        user = UserFactory()
        response = self.client.delete(reverse("ProjectUser-detail", args=(user.id,)))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertApiTechnicalError(
            response,
            "An error occurred while syncing with Keycloak : error reason",
        )
        self.assertTrue(ProjectUser.objects.filter(id=user.id).exists())

    def test_keycloak_404_delete_user(self):
        self.client.force_authenticate(UserFactory(groups=[get_superadmins_group()]))
        user = UserFactory()
        response = self.client.delete(reverse("ProjectUser-detail", args=(user.id,)))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ProjectUser.objects.filter(id=user.id).exists())


class ValidateUserTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()

    @patch("services.keycloak.interface.KeycloakService.send_email")
    def test_create_user_group_validation_no_permission(self, mocked):
        mocked.return_value = {}
        organization = self.organization
        organization_2 = OrganizationFactory()
        self.client.force_authenticate(UserFactory(groups=[organization.get_admins()]))
        payload = {
            "email": f"{faker.uuid4()}@{faker.domain_name()}",
            "given_name": faker.first_name(),
            "family_name": faker.last_name(),
            "roles_to_add": [
                organization.get_users().name,
                organization_2.get_users().name,
            ],
        }
        response = self.client.post(
            reverse("ProjectUser-list") + f"?organization={organization.code}",
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertApiPermissionError(
            response,
            "You do not have the permission to assign this role : "
            f"organization:#{organization_2.pk}:users",
        )


class FilterSearchOrderUserTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        ProjectUser.objects.all().delete()
        params = {
            "given_name": "test",
            "family_name": "test",
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
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["results"][0]["id"], self.user_a.id)
        self.assertEqual(content["results"][1]["id"], self.user_b.id)
        self.assertEqual(content["results"][2]["id"], self.user_c.id)
        self.assertEqual(content["results"][3]["id"], self.user_d.id)

    def test_order_by_job_reverse(self):
        response = self.client.get(reverse("ProjectUser-list") + "?ordering=-job")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["results"][0]["id"], self.user_d.id)
        self.assertEqual(content["results"][1]["id"], self.user_c.id)
        self.assertEqual(content["results"][2]["id"], self.user_b.id)
        self.assertEqual(content["results"][3]["id"], self.user_a.id)

    def test_order_by_role(self):
        response = self.client.get(
            reverse("ProjectUser-list")
            + f"?ordering=current_org_role&current_org_pk={self.organization.pk}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["results"][0]["id"], self.user_a.id)
        self.assertEqual(content["results"][1]["id"], self.user_b.id)
        self.assertEqual(content["results"][2]["id"], self.user_c.id)
        self.assertEqual(content["results"][3]["id"], self.user_d.id)

    def test_order_by_role_reverse(self):
        response = self.client.get(
            reverse("ProjectUser-list")
            + f"?ordering=-current_org_role&current_org_pk={self.organization.pk}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["results"][0]["id"], self.user_d.id)
        self.assertEqual(content["results"][1]["id"], self.user_c.id)
        self.assertEqual(content["results"][2]["id"], self.user_b.id)
        self.assertEqual(content["results"][3]["id"], self.user_a.id)

    def test_filter_by_role_admin(self):
        response = self.client.get(
            reverse("ProjectUser-list")
            + f"?current_org_role=admins&current_org_pk={self.organization.pk}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(len(content["results"]), 1)
        self.assertEqual(content["results"][0]["id"], self.user_a.id)

    def test_filter_by_role_facilitator(self):
        response = self.client.get(
            reverse("ProjectUser-list")
            + f"?current_org_role=facilitators&current_org_pk={self.organization.pk}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(len(content["results"]), 1)
        self.assertEqual(content["results"][0]["id"], self.user_b.id)

    def test_filter_by_role_user(self):
        response = self.client.get(
            reverse("ProjectUser-list")
            + f"?current_org_role=users&current_org_pk={self.organization.pk}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(len(content["results"]), 1)
        self.assertEqual(content["results"][0]["id"], self.user_c.id)

    def test_filter_by_multiple_roles(self):
        response = self.client.get(
            reverse("ProjectUser-list")
            + f"?current_org_role=admins,users&current_org_pk={self.organization.pk}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(len(content["results"]), 2)
        self.assertSetEqual(
            {u["id"] for u in content["results"]},
            {self.user_a.id, self.user_c.id},
        )

    def test_filter_by_organization(self):
        other_organization = OrganizationFactory(parent=self.organization)
        other_organization.admins.add(self.user_d)
        response = self.client.get(
            reverse("ProjectUser-list") + f"?organizations={self.organization.code}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(len(content["results"]), 3)
        self.assertSetEqual(
            {u["id"] for u in content["results"]},
            {self.user_a.id, self.user_b.id, self.user_c.id},
        )

    def test_search_by_job(self):
        response = self.client.get(reverse("ProjectUser-list") + "?search=ABC")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["results"][0]["id"], self.user_a.id)
        response = self.client.get(reverse("ProjectUser-list") + "?search=DEF")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["results"][0]["id"], self.user_b.id)
        response = self.client.get(reverse("ProjectUser-list") + "?search=GHI")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["results"][0]["id"], self.user_c.id)

    def test_search_with_current_org_pk(self):
        response = self.client.get(
            reverse("ProjectUser-list")
            + f"?search=ABC&current_org_pk={self.organization.pk}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["results"][0]["id"], self.user_a.id)
        response = self.client.get(
            reverse("ProjectUser-list")
            + f"?search=DEF&current_org_pk={self.organization.pk}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["results"][0]["id"], self.user_b.id)
        response = self.client.get(
            reverse("ProjectUser-list")
            + f"?search=GHI&current_org_pk={self.organization.pk}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["results"][0]["id"], self.user_c.id)


class MiscUserTestCase(JwtAPITestCase):
    def test_notifications_count(self):
        project = ProjectFactory()
        user = UserFactory()
        NotificationFactory.create_batch(
            5, receiver=user, project=project, is_viewed=False
        )
        NotificationFactory(receiver=user, project=project, is_viewed=True)
        NotificationFactory(project=project)
        self.client.force_authenticate(user)
        response = self.client.get(reverse("ProjectUser-detail", args=(user.id,)))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["notifications"], 5)

    @patch("services.keycloak.interface.KeycloakService.send_email")
    def test_language_from_organization(self, mocked):
        mocked.return_value = {}
        user = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(user)
        organization = OrganizationFactory(language="fr")
        payload = {
            "email": f"{faker.uuid4()}@{faker.domain_name()}",
            "given_name": faker.first_name(),
            "family_name": faker.last_name(),
            "roles_to_add": [organization.get_users().name],
        }
        response = self.client.post(
            reverse("ProjectUser-list") + f"?organization={organization.code}",
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["language"], "fr")
        keycloak_user = KeycloakService.get_user(response.data["keycloak_id"])
        self.assertEqual(keycloak_user["attributes"]["locale"], ["fr"])

    @patch("services.keycloak.interface.KeycloakService.send_email")
    def test_language_from_payload(self, mocked):
        mocked.return_value = {}
        user = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(user)
        organization = OrganizationFactory(language="en")
        payload = {
            "email": f"{faker.uuid4()}@{faker.domain_name()}",
            "given_name": faker.first_name(),
            "family_name": faker.last_name(),
            "roles_to_add": [organization.get_users().name],
            "language": "fr",
        }
        response = self.client.post(
            reverse("ProjectUser-list") + f"?organization={organization.code}",
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["language"], "fr")
        keycloak_user = KeycloakService.get_user(response.data["keycloak_id"])
        self.assertEqual(keycloak_user["attributes"]["locale"], ["fr"])

    def test_keycloak_attributes_updated(self):
        self.client.force_authenticate(UserFactory(groups=[get_superadmins_group()]))
        user = SeedUserFactory(language="en")
        KeycloakService._update_user(
            user.keycloak_id,
            {
                "username": user.email,
                "email": user.email,
                "firstName": user.given_name,
                "lastName": user.family_name,
                "attributes": {"attribute_1": ["value_1"], "locale": ["en"]},
            },
        )
        payload = {
            "language": "fr",
        }
        response = self.client.patch(
            reverse("ProjectUser-detail", args=(user.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["language"], "fr")
        keycloak_user = KeycloakService.get_user(user.keycloak_id)
        self.assertEqual(keycloak_user["attributes"]["locale"], ["fr"])
        self.assertEqual(keycloak_user["attributes"]["attribute_1"], ["value_1"])

    def test_add_organization_from_keycloak_attributes(self):
        organization = OrganizationFactory()
        payload = {
            "username": f"{faker.uuid4()}@{faker.domain_name()}",
            "email": f"{faker.uuid4()}@{faker.domain_name()}",
            "firstName": faker.first_name(),
            "lastName": faker.last_name(),
            "attributes": {"idp_organizations": [organization.code]},
        }
        keycloak_id = KeycloakService._create_user(payload)
        user = ProjectUser.import_from_keycloak(keycloak_id)
        self.assertIsNotNone(user)
        self.assertIn(user, organization.users.all())

    def test_get_current_org_role(self):
        users = UserFactory.create_batch(3)
        admins = UserFactory.create_batch(3)
        facilitators = UserFactory.create_batch(3)
        UserFactory.create_batch(3)
        organization = OrganizationFactory()
        organization.users.add(*users)
        organization.admins.add(*admins)
        organization.facilitators.add(*facilitators)
        url = reverse("ProjectUser-list")
        url += f"?current_org_pk={organization.pk}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["count"], 12)
        for user in response.data["results"]:
            if user["id"] in [u.id for u in admins]:
                self.assertEqual(user["current_org_role"], "admins")
            elif user["id"] in [u.id for u in facilitators]:
                self.assertEqual(user["current_org_role"], "facilitators")
            elif user["id"] in [u.id for u in users]:
                self.assertEqual(user["current_org_role"], "users")
            else:
                self.assertIsNone(user["current_org_role"])

    def test_get_current_org_role_two_roles(self):
        organization = OrganizationFactory()
        user = UserFactory()
        organization.users.add(user)
        organization.admins.add(user)
        url = reverse("ProjectUser-list")
        url += f"?current_org_pk={organization.pk}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["current_org_role"], "admins")

    def test_check_permissions(self):
        user = UserFactory()
        organization = OrganizationFactory()
        permissions = [
            "projects.view_project",
            f"organizations.view_org_project.{organization.pk}",
        ]
        response = self.client.get(
            reverse("ProjectUser-has-permissions", args=(user.id,))
            + f"?permissions={','.join(permissions)}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.json()["result"])

        assign_perm("organizations.view_org_project", user, organization)
        response = self.client.get(
            reverse("ProjectUser-has-permissions", args=(user.id,))
            + f"?permissions={','.join(permissions)}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.json()["result"])

        assign_perm("projects.view_project", user)
        response = self.client.get(
            reverse("ProjectUser-has-permissions", args=(user.id,))
            + f"?permissions={','.join(permissions)}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.json()["result"])

    def test_update_roles(self):
        organization_1 = OrganizationFactory()
        organization_2 = OrganizationFactory()
        project_1 = ProjectFactory(organizations=[organization_1])
        project_2 = ProjectFactory(organizations=[organization_2])
        people_group_1 = PeopleGroupFactory(organization=organization_1)
        people_group_2 = PeopleGroupFactory(organization=organization_2)
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
            reverse("ProjectUser-detail", args=(user.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(len(content["roles"]), 8)
        self.assertSetEqual(
            set(content["roles"]),
            {
                project_1.get_owners().name,
                project_2.get_members().name,
                people_group_2.get_members().name,
                people_group_1.get_leaders().name,
                organization_1.get_admins().name,
                organization_2.get_users().name,
                get_superadmins_group().name,
                get_default_group().name,
            },
        )

    def test_get_slug(self):
        given_name = faker.first_name()
        family_name = faker.last_name()
        user = UserFactory(given_name=given_name, family_name=family_name)
        slug_base = "-".join([given_name.lower(), family_name.lower()])
        self.assertEqual(user.slug, slug_base)
        user = UserFactory(given_name=given_name, family_name=family_name)
        self.assertEqual(user.slug, f"{slug_base}-1")
        user = UserFactory(given_name=given_name, family_name=family_name)
        self.assertEqual(user.slug, f"{slug_base}-2")
        user = UserFactory(given_name="", family_name="")
        slug_base = user.email.split("@")[0].lower()
        self.assertEqual(user.slug, slug_base)

    def test_integer_slug(self):
        given_name = str(faker.pyint())
        family_name = ""
        user = UserFactory(given_name=given_name, family_name=family_name)
        self.assertEqual(user.slug, f"user-{given_name}")

    def test_uuid_slug(self):
        given_name = str(faker.uuid4())
        family_name = ""
        user = UserFactory(given_name=given_name, family_name=family_name)
        self.assertEqual(user.slug, f"user-{given_name}")

    def test_multiple_lookups(self):
        user = UserFactory()
        response = self.client.get(reverse("ProjectUser-detail", args=(user.id,)))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["slug"], user.slug)
        self.assertEqual(content["keycloak_id"], user.keycloak_id)
        response = self.client.get(reverse("ProjectUser-detail", args=(user.slug,)))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["id"], user.id)
        self.assertEqual(content["keycloak_id"], user.keycloak_id)
        response = self.client.get(
            reverse("ProjectUser-detail", args=(user.keycloak_id,))
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["id"], user.id)
        self.assertEqual(content["slug"], user.slug)
