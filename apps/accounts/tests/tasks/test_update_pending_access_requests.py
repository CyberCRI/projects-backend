import datetime
from unittest.mock import patch

from django.urls import reverse
from django.utils.timezone import make_aware
from faker import Faker
from rest_framework import status

from apps.accounts.factories import PeopleGroupFactory, UserFactory
from apps.accounts.tasks import update_new_user_pending_access_requests
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase
from apps.invitations.factories import AccessRequestFactory, InvitationFactory
from apps.invitations.models import AccessRequest
from apps.organizations.factories import OrganizationFactory

faker = Faker()


class UpdateNewUserPendingAccessRequestsTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()

    @patch("services.keycloak.interface.KeycloakService.send_email")
    @patch("apps.accounts.tasks.update_new_user_pending_access_requests.delay")
    def test_task_is_called_on_admin_created(self, mocked_task, mocked_email):
        mocked_email.return_value = {}
        user = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(user)
        payload = {
            "email": f"{faker.uuid4()}@{faker.domain_name()}",
            "given_name": faker.first_name(),
            "family_name": faker.last_name(),
            "roles_to_add": [self.organization.get_users().name],
        }
        response = self.client.post(
            reverse("ProjectUser-list") + f"?organization={self.organization.code}",
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        content = response.json()
        mocked_task.assert_called_once_with(content["id"], self.organization.code)

    @patch("services.keycloak.interface.KeycloakService.send_email")
    @patch("apps.accounts.tasks.update_new_user_pending_access_requests.delay")
    def test_create_user_with_invitation(self, mocked_task, mocked_email):
        mocked_email.return_value = {}
        invitation = InvitationFactory(
            organization=self.organization,
            people_group=PeopleGroupFactory(organization=self.organization),
            expire_at=make_aware(datetime.datetime.now() + datetime.timedelta(1)),
        )
        self.client.force_authenticate(  # nosec
            token=invitation.token, token_type="Invite"
        )
        payload = {
            "email": f"{faker.uuid4()}@{faker.domain_name()}",
            "given_name": faker.first_name(),
            "family_name": faker.last_name(),
            "password": faker.password(),
        }
        response = self.client.post(
            reverse("ProjectUser-list") + f"?organization={self.organization.code}",
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        content = response.json()
        mocked_task.assert_called_once_with(content["id"], self.organization.code)

    def test_update_new_user_pending_access_requests(self):
        organization_2 = OrganizationFactory()
        email = faker.email()
        user = UserFactory(email=email, groups=[self.organization.get_users()])
        access_request_1 = AccessRequestFactory(
            organization=self.organization,
            status=AccessRequest.Status.PENDING,
            user=None,
            email=email,
        )
        access_request_2 = AccessRequestFactory(
            organization=self.organization,
            status=AccessRequest.Status.PENDING,
            user=None,
        )
        access_request_3 = AccessRequestFactory(
            organization=organization_2,
            status=AccessRequest.Status.PENDING,
            user=None,
            email=email,
        )
        access_request_4 = AccessRequestFactory(
            organization=organization_2,
            status=AccessRequest.Status.PENDING,
            user=None,
        )
        update_new_user_pending_access_requests(user.pk, self.organization.code)
        access_request_1.refresh_from_db()
        access_request_2.refresh_from_db()
        access_request_3.refresh_from_db()
        access_request_4.refresh_from_db()
        self.assertEqual(access_request_1.user, user)
        self.assertEqual(access_request_1.status, AccessRequest.Status.ACCEPTED)
        self.assertIsNone(access_request_2.user)
        self.assertEqual(access_request_2.status, AccessRequest.Status.PENDING)
        self.assertEqual(access_request_3.user, user)
        self.assertEqual(access_request_3.status, AccessRequest.Status.PENDING)
        self.assertIsNone(access_request_4.user)
        self.assertEqual(access_request_4.status, AccessRequest.Status.PENDING)
