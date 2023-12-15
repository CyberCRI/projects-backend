import datetime
from unittest.mock import Mock, patch

from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart
from django.urls import reverse
from django.utils.timezone import make_aware
from faker import Faker
from googleapiclient.errors import HttpError
from guardian.shortcuts import assign_perm
from parameterized import parameterized
from rest_framework import status

from apps.accounts.factories import AccessRequestFactory, PeopleGroupFactory, SeedUserFactory, UserFactory
from apps.accounts.models import AccessRequest, ProjectUser
from apps.accounts.utils import get_default_group, get_superadmins_group
from apps.commons.test import JwtAPITestCase, TestRoles
from apps.invitations.factories import InvitationFactory
from apps.notifications.factories import NotificationFactory
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory
from keycloak import KeycloakDeleteError, KeycloakGetError
from services.keycloak.factories import RemoteKeycloakAccountFactory
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


class AcceptAccessRequestTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory(access_request_enabled=True)

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
    def test_accept_access_requests(self, role, expected_code, mocked):
        mocked.return_value = {}
        organization = OrganizationFactory()
        request_access_user = UserFactory()
        authentified_access_request = AccessRequestFactory(user=request_access_user, organization=organization)
        anonymous_access_request = AccessRequestFactory.create_batch(3, organization=organization)
        access_requests = [authentified_access_request, *anonymous_access_request]

        user = self.get_parameterized_test_user(role, instances=[organization])
        self.client.force_authenticate(user)
        payload = {
            "access_requests": [access_request.id for access_request in access_requests],
        }
        response = self.client.post(
            reverse("AccessRequest-accept", args=(organization.code,)),
            data=payload,
        )
        assert response.status_code == expected_code
        if expected_code == status.HTTP_200_OK:
            content = response.json()
            assert all(result["status"] == "success" for result in content["results"])
            
            authentified_access_request.refresh_from_db()
            assert authentified_access_request.status == AccessRequest.Status.ACCEPTED
            assert request_access_user in organization.users

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
            (TestRoles.SUPERADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_ADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_FACILITATOR, status.HTTP_403_FORBIDDEN),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
        ]
    )
    @patch("services.keycloak.interface.KeycloakService.send_email")
    def test_decline_access_request(self, role, expected_code, mocked):
        mocked.return_value = {}
        organization = OrganizationFactory()
        request_access_user = UserFactory()
        authentified_access_request = AccessRequestFactory(user=request_access_user, organization=organization)
        anonymous_access_request = AccessRequestFactory.create_batch(3, organization=organization)
        access_requests = [authentified_access_request, *anonymous_access_request]
        user = self.get_parameterized_test_user(role, instances=[organization])
        self.client.force_authenticate(user)
        payload = {
            "access_requests": [access_request.id for access_request in access_requests],
        }
        response = self.client.post(
            reverse("AccessRequest-decline", args=(organization.code,)),
            data=payload,
        )
        assert response.status_code == expected_code
        if expected_code == status.HTTP_204_NO_CONTENT:
            content = response.json()
            assert all(result["status"] == "success" for result in content["results"])

            authentified_access_request.refresh_from_db()
            assert authentified_access_request.status == AccessRequest.Status.DECLINED
            assert request_access_user not in organization.users

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

    def test_create_request_access_in_unauthorized_organization(self):
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
        assert content["detail"] == "This organization does not accept access requests."

    def test_create_access_user_in_organization(self):
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
        assert content["detail"] == ""

    def test_create_request_access_existing_user(self):
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
        assert content["detail"] == ""

    def test_accept_access_requests_from_different_organizations(self):
        user = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(user)
        access_request_1 = AccessRequestFactory(organization=self.organization)
        access_request_2 = AccessRequestFactory()
        payload = {
            "access_requests": [access_request_1.id, access_request_2.id],
        }
        response = self.client.post(
            reverse("AccessRequest-accept", args=(self.organization.code,)),
            data=payload,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        content = response.json()
        assert content["detail"] == ""

    def test_accept_accepted_access_request(self):
        user = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(user)
        access_request = AccessRequestFactory(organization=self.organization, status=AccessRequest.Status.ACCEPTED)
        payload = {
            "access_requests": [access_request.id],
        }
        response = self.client.post(
            reverse("AccessRequest-accept", args=(self.organization.code,)),
            data=payload,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        content = response.json()
        assert content["detail"] == "You can only accept or decline pending access requests."

    def test_accept_access_request_keycloak_post_error(self):
        user = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(user)
        existing_username = faker.email()
        KeycloakService._create_user(
            {
                "email": existing_username,
                "username": existing_username,
                "enabled": True,
                "firstName": faker.first_name(),
                "lastName": faker.last_name(),
            }
        )
        access_request = AccessRequestFactory(organization=self.organization, email=existing_username)
        payload = {
            "access_requests": [access_request.id],
        }
        response = self.client.post(
            reverse("AccessRequest-accept", args=(self.organization.code,)),
            data=payload,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        content = response.json()
        assert content["detail"] == ""

    @patch("services.keycloak.interface.KeycloakService.send_email")
    def test_accept_access_request_keycloak_email_error(self, mocked):
        mocked.side_effect = KeycloakGetError("email error")
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
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        content = response.json()
        assert content["detail"] == ""
