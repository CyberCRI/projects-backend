import json
from unittest.mock import patch

from django.urls import reverse
from faker import Faker
from keycloak import KeycloakError, KeycloakGetError, KeycloakPostError
from parameterized import parameterized
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.accounts.models import ProjectUser
from apps.accounts.utils import get_default_group, get_superadmins_group
from apps.commons.test import JwtAPITestCase, TestRoles
from apps.invitations.factories import AccessRequestFactory
from apps.invitations.models import AccessRequest
from apps.organizations.factories import OrganizationFactory
from services.keycloak.interface import KeycloakService

faker = Faker()


class CreateAccessRequestTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory(
            access_request_enabled=True, language="en"
        )
        cls.admins = UserFactory.create_batch(3, groups=[cls.organization.get_admins()])
        cls.user_1 = UserFactory(groups=[cls.organization.get_users()])

    def test_create_access_request_anonymous(self):
        payload = {
            "email": faker.email(),
            "given_name": faker.first_name(),
            "family_name": faker.last_name(),
            "job": faker.sentence(),
            "message": faker.text(),
        }
        response = self.client.post(
            reverse("AccessRequest-list", args=(self.organization.code,)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        content = response.json()
        self.assertEqual(content["organization"], self.organization.code)
        self.assertEqual(content["status"], AccessRequest.Status.PENDING.value)
        self.assertEqual(content["email"], payload["email"])
        self.assertEqual(content["given_name"], payload["given_name"])
        self.assertEqual(content["family_name"], payload["family_name"])
        self.assertEqual(content["job"], payload["job"])
        self.assertEqual(content["message"], payload["message"])

    def test_create_access_request_authenticated(self):
        user = UserFactory()
        self.client.force_authenticate(user)
        payload = {
            "email": faker.email(),
            "given_name": faker.first_name(),
            "family_name": faker.last_name(),
            "job": faker.sentence(),
            "message": faker.text(),
        }
        response = self.client.post(
            reverse("AccessRequest-list", args=(self.organization.code,)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        content = response.json()
        self.assertEqual(content["organization"], self.organization.code)
        self.assertEqual(content["status"], AccessRequest.Status.PENDING.value)
        self.assertEqual(content["email"], user.email)
        self.assertEqual(content["given_name"], user.given_name)
        self.assertEqual(content["family_name"], user.family_name)
        self.assertEqual(content["job"], user.job)
        self.assertEqual(content["message"], payload["message"])


class ListAccessRequestTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory(access_request_enabled=True)
        cls.access_requests = AccessRequestFactory.create_batch(
            3, organization=cls.organization
        )

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_ADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_FACILITATOR, status.HTTP_403_FORBIDDEN),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_list_access_requests(self, role, expected_code):
        user = self.get_parameterized_test_user(role, instances=[self.organization])
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("AccessRequest-list", args=(self.organization.code,)),
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_200_OK:
            content = response.json()["results"]
            self.assertEqual(len(content), len(self.access_requests))
            self.assertSetEqual(
                {r.id for r in self.access_requests}, {r["id"] for r in content}
            )


class FilterOrderUserTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.access_requests_a = AccessRequestFactory(
            organization=cls.organization, status=AccessRequest.Status.ACCEPTED
        )
        cls.access_requests_b = AccessRequestFactory(
            organization=cls.organization, status=AccessRequest.Status.DECLINED
        )
        cls.access_requests_c = AccessRequestFactory(
            organization=cls.organization, status=AccessRequest.Status.PENDING
        )
        cls.access_requests_d = AccessRequestFactory(
            organization=cls.organization, status=AccessRequest.Status.PENDING
        )
        cls.superadmin = UserFactory(groups=[get_superadmins_group()])

    def setUp(self) -> None:
        super().setUp()
        self.client.force_authenticate(self.superadmin)

    def test_order_by_status(self):
        response = self.client.get(
            reverse("AccessRequest-list", args=(self.organization.code,))
            + "?ordering=status"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["results"][0]["status"], self.access_requests_a.status
        )
        self.assertEqual(
            response.data["results"][1]["status"], self.access_requests_b.status
        )
        self.assertSetEqual(
            {
                response.data["results"][2]["status"],
                response.data["results"][3]["status"],
            },
            {self.access_requests_c.status, self.access_requests_d.status},
        )

    def test_order_by_status_reverse(self):
        response = self.client.get(
            reverse("AccessRequest-list", args=(self.organization.code,))
            + "?ordering=-status"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertSetEqual(
            {
                response.data["results"][0]["status"],
                response.data["results"][1]["status"],
            },
            {self.access_requests_c.status, self.access_requests_d.status},
        )
        self.assertEqual(
            response.data["results"][2]["status"], self.access_requests_b.status
        )
        self.assertEqual(
            response.data["results"][3]["status"], self.access_requests_a.status
        )

    def test_order_by_creation_date(self):
        response = self.client.get(
            reverse("AccessRequest-list", args=(self.organization.code,))
            + "?ordering=created_at"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLess(
            response.data["results"][0]["created_at"],
            response.data["results"][1]["created_at"],
        )
        self.assertLess(
            response.data["results"][1]["created_at"],
            response.data["results"][2]["created_at"],
        )
        self.assertLess(
            response.data["results"][2]["created_at"],
            response.data["results"][3]["created_at"],
        )

    def test_order_by_creation_date_reverse(self):
        response = self.client.get(
            reverse("AccessRequest-list", args=(self.organization.code,))
            + "?ordering=-created_at"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertLess(
            response.data["results"][3]["created_at"],
            response.data["results"][2]["created_at"],
        )
        self.assertLess(
            response.data["results"][2]["created_at"],
            response.data["results"][1]["created_at"],
        )
        self.assertLess(
            response.data["results"][1]["created_at"],
            response.data["results"][0]["created_at"],
        )

    def test_filter_by_status_pending(self):
        self.client.force_authenticate(
            UserFactory(groups=[self.organization.get_admins()])
        )
        response = self.client.get(
            reverse("AccessRequest-list", args=(self.organization.code,))
            + f"?status={AccessRequest.Status.PENDING.value}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertEqual(response.data["results"][0]["id"], self.access_requests_c.id)
        self.assertEqual(response.data["results"][1]["id"], self.access_requests_d.id)

    def test_filter_by_status_accepted(self):
        response = self.client.get(
            reverse("AccessRequest-list", args=(self.organization.code,))
            + f"?status={AccessRequest.Status.ACCEPTED.value}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], self.access_requests_a.id)

    def test_filter_by_status_declined(self):
        response = self.client.get(
            reverse("AccessRequest-list", args=(self.organization.code,))
            + f"?status={AccessRequest.Status.DECLINED.value}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["id"], self.access_requests_b.id)


class AcceptAccessRequestTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory(access_request_enabled=True)

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_ADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_FACILITATOR, status.HTTP_403_FORBIDDEN),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
        ]
    )
    @patch("services.keycloak.interface.KeycloakService.send_email")
    def test_accept_access_requests(self, role, expected_code, mocked):
        mocked.return_value = {}
        organization = self.organization
        request_access_user = UserFactory()
        authentified_access_request = AccessRequestFactory(
            user=request_access_user, organization=organization
        )
        anonymous_access_request = AccessRequestFactory.create_batch(
            3, organization=organization
        )
        access_requests = [authentified_access_request, *anonymous_access_request]

        user = self.get_parameterized_test_user(role, instances=[organization])
        self.client.force_authenticate(user)
        payload = {
            "access_requests": [
                access_request.id for access_request in access_requests
            ],
        }
        response = self.client.post(
            reverse("AccessRequest-accept", args=(organization.code,)),
            data=payload,
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_200_OK:
            content = response.json()
            self.assertEqual(len(content["success"]), 4)
            self.assertEqual(len(content["error"]), 0)
            self.assertEqual(len(content["warning"]), 0)

            authentified_access_request.refresh_from_db()
            self.assertEqual(
                authentified_access_request.status, AccessRequest.Status.ACCEPTED
            )
            self.assertIn(request_access_user, organization.users.all())

            for access_request in anonymous_access_request:
                access_request.refresh_from_db()
                self.assertEqual(access_request.status, AccessRequest.Status.ACCEPTED)
                user = ProjectUser.objects.filter(email=access_request.email)
                self.assertTrue(user.exists())
                user = user.get()
                self.assertTrue(user.onboarding_status["show_welcome"])
                self.assertEqual(user.signed_terms_and_conditions, {})
                self.assertEqual(user.email, access_request.email)
                self.assertEqual(user.given_name, access_request.given_name)
                self.assertEqual(user.family_name, access_request.family_name)
                self.assertEqual(user.job, access_request.job)
                self.assertEqual(user.groups.count(), 2)
                self.assertSetEqual(
                    {*user.groups.all()},
                    {
                        get_default_group(),
                        organization.get_users(),
                    },
                )
                self.assertTrue(hasattr(user, "keycloak_account"))
                keycloak_user = KeycloakService.get_user(user.keycloak_id)
                self.assertIsNotNone(keycloak_user)
                self.assertSetEqual(
                    set(keycloak_user["requiredActions"]),
                    {"VERIFY_EMAIL", "UPDATE_PASSWORD"},
                )

    def test_accept_access_requests_with_other_requests(self):
        access_request = AccessRequestFactory(organization=self.organization)
        access_request_2 = AccessRequestFactory(email=access_request.email)
        self.client.force_authenticate(UserFactory(groups=[get_superadmins_group()]))
        payload = {
            "access_requests": [access_request.id],
        }
        response = self.client.post(
            reverse("AccessRequest-accept", args=(self.organization.code,)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        access_request.refresh_from_db()
        access_request_2.refresh_from_db()
        self.assertEqual(access_request.status, AccessRequest.Status.ACCEPTED)
        self.assertEqual(access_request_2.status, AccessRequest.Status.PENDING)
        user = ProjectUser.objects.filter(email=access_request.email)
        self.assertTrue(user.exists())
        self.assertEqual(access_request_2.user, user.get())


class DeclineAccessRequestTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_ADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_FACILITATOR, status.HTTP_403_FORBIDDEN),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
        ]
    )
    @patch("services.keycloak.interface.KeycloakService.send_email")
    def test_decline_access_request(self, role, expected_code, mocked):
        mocked.return_value = {}
        organization = OrganizationFactory()
        request_access_user = UserFactory()
        authentified_access_request = AccessRequestFactory(
            user=request_access_user, organization=organization
        )
        anonymous_access_request = AccessRequestFactory.create_batch(
            3, organization=organization
        )
        access_requests = [authentified_access_request, *anonymous_access_request]
        user = self.get_parameterized_test_user(role, instances=[organization])
        self.client.force_authenticate(user)
        payload = {
            "access_requests": [
                access_request.id for access_request in access_requests
            ],
        }
        response = self.client.post(
            reverse("AccessRequest-decline", args=(organization.code,)),
            data=payload,
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_200_OK:
            content = response.json()
            self.assertEqual(len(content["success"]), 4)
            self.assertEqual(len(content["error"]), 0)
            self.assertEqual(len(content["warning"]), 0)

            authentified_access_request.refresh_from_db()
            self.assertEqual(
                authentified_access_request.status, AccessRequest.Status.DECLINED
            )
            self.assertNotIn(request_access_user, organization.users.all())

            for access_request in anonymous_access_request:
                access_request.refresh_from_db()
                self.assertEqual(access_request.status, AccessRequest.Status.DECLINED)
                user = ProjectUser.objects.filter(email=access_request.email)
                self.assertFalse(user.exists())


class ValidateRequestAccessTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory(access_request_enabled=True)

    @staticmethod
    def mocked_keycloak_error(
        keycloak_error: KeycloakError, response_code: int = 400, error_message: str = ""
    ):
        def inner(*args, **kwargs):
            response_body = json.dumps({"errorMessage": error_message}).encode()
            raise keycloak_error(error_message, response_code, response_body)

        return inner

    def test_create_access_request_in_unauthorized_organization(self):
        organization = OrganizationFactory(access_request_enabled=False)
        payload = {
            "email": faker.email(),
            "given_name": faker.first_name(),
            "family_name": faker.last_name(),
            "job": faker.sentence(),
            "message": faker.text(),
        }
        response = self.client.post(
            reverse("AccessRequest-list", args=(organization.code,)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertApiValidationError(
            response,
            {"organization": ["This organization does not accept access requests"]},
        )

    def test_create_access_request_user_in_organization(self):
        user = UserFactory(groups=[self.organization.get_users()])
        self.client.force_authenticate(user)
        payload = {
            "email": faker.email(),
            "given_name": faker.first_name(),
            "family_name": faker.last_name(),
            "job": faker.sentence(),
            "message": faker.text(),
        }
        response = self.client.post(
            reverse("AccessRequest-list", args=(self.organization.code,)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertApiValidationError(
            response,
            {"user": ["This user is already a member of this organization"]},
        )

    def test_create_access_request_existing_user(self):
        user = UserFactory()
        payload = {
            "email": user.email,
            "given_name": faker.first_name(),
            "family_name": faker.last_name(),
            "job": faker.sentence(),
            "message": faker.text(),
        }
        response = self.client.post(
            reverse("AccessRequest-list", args=(self.organization.code,)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertApiValidationError(
            response,
            {"email": ["A user with this email already exists"]},
        )

    def test_create_access_request_existing_user_case_insensitive(self):
        email = faker.email().lower()
        upper_email = email.upper()

        UserFactory(email=email)
        payload = {
            "email": upper_email,
            "given_name": faker.first_name(),
            "family_name": faker.last_name(),
            "job": faker.sentence(),
            "message": faker.text(),
        }
        response = self.client.post(
            reverse("AccessRequest-list", args=(self.organization.code,)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertApiValidationError(
            response,
            {"email": ["A user with this email already exists"]},
        )

    def test_create_duplicate_access_request_anonymous(self):
        access_request = AccessRequestFactory(organization=self.organization)
        payload = {
            "email": access_request.email,
            "given_name": faker.first_name(),
            "family_name": faker.last_name(),
            "job": faker.sentence(),
            "message": faker.text(),
        }
        response = self.client.post(
            reverse("AccessRequest-list", args=(self.organization.code,)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertApiValidationError(
            response,
            {"email": ["An access request for this email already exists"]},
        )

    def test_create_duplicate_access_request_anonymous_case_insensitive(self):
        email = faker.email().lower()
        upper_email = email.upper()
        AccessRequestFactory(organization=self.organization, email=email)
        payload = {
            "email": upper_email,
            "given_name": faker.first_name(),
            "family_name": faker.last_name(),
            "job": faker.sentence(),
            "message": faker.text(),
        }
        response = self.client.post(
            reverse("AccessRequest-list", args=(self.organization.code,)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertApiValidationError(
            response,
            {"email": ["An access request for this email already exists"]},
        )

    def test_create_duplicate_access_request_for_user(self):
        user = UserFactory()
        AccessRequestFactory(organization=self.organization, user=user)
        self.client.force_authenticate(user)
        response = self.client.post(
            reverse("AccessRequest-list", args=(self.organization.code,)),
            data={},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertApiValidationError(
            response,
            {"user": ["An access request for this user already exists"]},
        )

    def test_accept_access_requests_from_different_organization(self):
        user = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(user)
        access_request = AccessRequestFactory()
        payload = {
            "access_requests": [access_request.id],
        }
        response = self.client.post(
            reverse("AccessRequest-accept", args=(self.organization.code,)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(len(content["error"]), 1)
        self.assertEqual(len(content["success"]), 0)
        self.assertEqual(len(content["warning"]), 0)
        self.assertEqual(content["error"][0]["id"], access_request.id)
        self.assertEqual(
            content["error"][0]["message"],
            "This access request is not for the current organization.",
        )

    def test_accept_accepted_access_request(self):
        user = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(user)
        access_request = AccessRequestFactory(
            organization=self.organization, status=AccessRequest.Status.ACCEPTED
        )
        payload = {
            "access_requests": [access_request.id],
        }
        response = self.client.post(
            reverse("AccessRequest-accept", args=(self.organization.code,)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(len(content["error"]), 1)
        self.assertEqual(len(content["success"]), 0)
        self.assertEqual(len(content["warning"]), 0)
        self.assertEqual(content["error"][0]["id"], access_request.id)
        self.assertEqual(
            content["error"][0]["message"],
            "This access request has already been processed.",
        )

    def test_decline_access_requests_from_different_organization(self):
        user = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(user)
        access_request = AccessRequestFactory()
        payload = {
            "access_requests": [access_request.id],
        }
        response = self.client.post(
            reverse("AccessRequest-decline", args=(self.organization.code,)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(len(content["error"]), 1)
        self.assertEqual(len(content["success"]), 0)
        self.assertEqual(len(content["warning"]), 0)
        self.assertEqual(content["error"][0]["id"], access_request.id)
        self.assertEqual(
            content["error"][0]["message"],
            "This access request is not for the current organization.",
        )

    def test_decline_accepted_access_request(self):
        user = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(user)
        access_request = AccessRequestFactory(
            organization=self.organization, status=AccessRequest.Status.ACCEPTED
        )
        payload = {
            "access_requests": [access_request.id],
        }
        response = self.client.post(
            reverse("AccessRequest-decline", args=(self.organization.code,)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(len(content["error"]), 1)
        self.assertEqual(len(content["success"]), 0)
        self.assertEqual(len(content["warning"]), 0)
        self.assertEqual(content["error"][0]["id"], access_request.id)
        self.assertEqual(
            content["error"][0]["message"],
            "This access request has already been processed.",
        )

    @patch("services.keycloak.interface.KeycloakService.create_user")
    def test_accept_access_request_keycloak_post_error(self, mocked):
        mocked.side_effect = self.mocked_keycloak_error(
            KeycloakPostError, 409, "User exists with same username"
        )
        user = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(user)
        access_request = AccessRequestFactory(organization=self.organization)
        payload = {
            "access_requests": [access_request.id],
        }
        response = self.client.post(
            reverse("AccessRequest-accept", args=(self.organization.code,)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(len(content["error"]), 1)
        self.assertEqual(len(content["success"]), 0)
        self.assertEqual(len(content["warning"]), 0)
        self.assertEqual(content["error"][0]["id"], access_request.id)
        self.assertEqual(
            content["error"][0]["message"],
            "Keycloak error : User exists with same username",
        )

    @patch("services.keycloak.interface.KeycloakService.send_email")
    def test_accept_access_request_keycloak_email_error(self, mocked):
        mocked.side_effect = self.mocked_keycloak_error(
            KeycloakGetError, 404, "User not found"
        )
        user = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(user)
        access_request = AccessRequestFactory(organization=self.organization)
        payload = {
            "access_requests": [access_request.id],
        }
        response = self.client.post(
            reverse("AccessRequest-accept", args=(self.organization.code,)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(len(content["error"]), 0)
        self.assertEqual(len(content["success"]), 0)
        self.assertEqual(len(content["warning"]), 1)
        self.assertEqual(content["warning"][0]["id"], access_request.id)
        self.assertEqual(
            content["warning"][0]["message"], "Confirmation email not sent to user"
        )
