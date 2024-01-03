import json
from unittest.mock import patch

from django.urls import reverse
from faker import Faker
from parameterized import parameterized
from rest_framework import status

from apps.accounts.factories import AccessRequestFactory, UserFactory
from apps.accounts.models import AccessRequest, ProjectUser
from apps.accounts.utils import get_default_group, get_superadmins_group
from apps.commons.test import JwtAPITestCase, TestRoles
from apps.organizations.factories import OrganizationFactory
from keycloak import KeycloakError, KeycloakGetError, KeycloakPostError
from services.keycloak.interface import KeycloakService

faker = Faker()


class CreateAccessRequestTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory(access_request_enabled=True)

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
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["organization"] == self.organization.code
        assert response.data["status"] == AccessRequest.Status.PENDING.value
        assert response.data["email"] == payload["email"]
        assert response.data["given_name"] == payload["given_name"]
        assert response.data["family_name"] == payload["family_name"]
        assert response.data["job"] == payload["job"]
        assert response.data["message"] == payload["message"]

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
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["organization"] == self.organization.code
        assert response.data["status"] == AccessRequest.Status.PENDING.value
        assert response.data["email"] == user.email
        assert response.data["given_name"] == user.given_name
        assert response.data["family_name"] == user.family_name
        assert response.data["job"] == user.job
        assert response.data["message"] == payload["message"]


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
        assert response.status_code == expected_code
        if expected_code == status.HTTP_200_OK:
            content = response.json()["results"]
            assert len(content) == len(self.access_requests)
            assert {r.id for r in self.access_requests} == {r["id"] for r in content}


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
        assert response.status_code == expected_code
        if expected_code == status.HTTP_200_OK:
            content = response.json()
            assert len(content["success"]) == 4
            assert len(content["error"]) == 0
            assert len(content["warning"]) == 0

            authentified_access_request.refresh_from_db()
            assert authentified_access_request.status == AccessRequest.Status.ACCEPTED
            assert request_access_user in organization.users.all()

            for access_request in anonymous_access_request:
                access_request.refresh_from_db()
                assert access_request.status == AccessRequest.Status.ACCEPTED
                user = ProjectUser.objects.filter(email=access_request.email)
                assert user.exists()
                user = user.get()
                assert user.onboarding_status["show_welcome"] is True
                assert user.email == access_request.email
                assert user.given_name == access_request.given_name
                assert user.family_name == access_request.family_name
                assert user.job == access_request.job
                assert user.groups.count() == 2
                assert {*user.groups.all()} == {
                    get_default_group(),
                    organization.get_users(),
                }
                assert hasattr(user, "keycloak_account")
                keycloak_user = KeycloakService.get_user(user.keycloak_id)
                assert keycloak_user is not None
                assert set(keycloak_user["requiredActions"]) == {
                    "VERIFY_EMAIL",
                    "UPDATE_PASSWORD",
                }


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
        assert response.status_code == expected_code
        if expected_code == status.HTTP_200_OK:
            content = response.json()
            assert len(content["success"]) == 4
            assert len(content["error"]) == 0
            assert len(content["warning"]) == 0

            authentified_access_request.refresh_from_db()
            assert authentified_access_request.status == AccessRequest.Status.DECLINED
            assert request_access_user not in organization.users.all()

            for access_request in anonymous_access_request:
                access_request.refresh_from_db()
                assert access_request.status == AccessRequest.Status.DECLINED
                user = ProjectUser.objects.filter(email=access_request.email)
                assert not user.exists()


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
        organization = OrganizationFactory()
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
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        content = response.json()
        assert content["organization"] == [
            "This organization does not accept access requests."
        ]

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
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        content = response.json()
        assert content["user"] == [
            "This user is already a member of this organization."
        ]

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
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        content = response.json()
        assert content["email"] == ["A user with this email already exists."]

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
        assert response.status_code == status.HTTP_200_OK
        content = response.json()
        assert len(content["error"]) == 1
        assert len(content["success"]) == 0
        assert len(content["warning"]) == 0
        assert content["error"][0]["id"] == access_request.id
        assert (
            content["error"][0]["message"]
            == "This access request is not for the current organization."
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
        assert response.status_code == status.HTTP_200_OK
        content = response.json()
        assert len(content["error"]) == 1
        assert len(content["success"]) == 0
        assert len(content["warning"]) == 0
        assert content["error"][0]["id"] == access_request.id
        assert (
            content["error"][0]["message"]
            == "This access request has already been processed."
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
        assert response.status_code == status.HTTP_200_OK
        content = response.json()
        assert len(content["error"]) == 1
        assert len(content["success"]) == 0
        assert len(content["warning"]) == 0
        assert content["error"][0]["id"] == access_request.id
        assert (
            content["error"][0]["message"]
            == "This access request is not for the current organization."
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
        assert response.status_code == status.HTTP_200_OK
        content = response.json()
        assert len(content["error"]) == 1
        assert len(content["success"]) == 0
        assert len(content["warning"]) == 0
        assert content["error"][0]["id"] == access_request.id
        assert (
            content["error"][0]["message"]
            == "This access request has already been processed."
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
        assert response.status_code == status.HTTP_200_OK
        content = response.json()
        assert len(content["error"]) == 1
        assert len(content["success"]) == 0
        assert len(content["warning"]) == 0
        assert content["error"][0]["id"] == access_request.id
        assert (
            content["error"][0]["message"]
            == "Keycloak error : User exists with same username"
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
        assert response.status_code == status.HTTP_200_OK
        content = response.json()
        assert len(content["error"]) == 0
        assert len(content["success"]) == 0
        assert len(content["warning"]) == 1
        assert content["warning"][0]["id"] == access_request.id
        assert content["warning"][0]["message"] == "Confirmation email not sent to user"
