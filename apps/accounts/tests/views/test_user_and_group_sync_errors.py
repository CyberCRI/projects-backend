import uuid
from unittest import mock

import pytest
from django.conf import settings
from django.urls import reverse
from faker import Faker
from googleapiclient.errors import HttpError

from apps.accounts.factories import PeopleGroupFactory, SeedUserFactory, UserFactory
from apps.accounts.models import PeopleGroup, ProjectUser
from apps.commons.test import JwtAPITestCase
from apps.organizations.factories import OrganizationFactory
from keycloak import KeycloakGetError
from services.keycloak.interface import KeycloakService

faker = Faker()


class GoogleKeycloakSyncErrorsTestCase(JwtAPITestCase):
    @staticmethod
    def mocked_google_error(code=400):
        def raise_error(*args, **kwargs):
            raise HttpError(
                resp=mock.Mock(status=code, reason="error reason"),
                content=b'{"error": {"errors": [{"reason": "error reason"}]}}',
            )

        return raise_error

    def test_keycloak_error_create_user(self):
        self.client.force_authenticate(
            user=UserFactory(permissions=[("accounts.add_projectuser", None)])
        )
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
        self.client.force_authenticate(
            user=UserFactory(permissions=[("accounts.change_projectuser", None)])
        )
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

    def test_keycloak_error_delete_user(self):
        self.client.force_authenticate(
            user=UserFactory(permissions=[("accounts.delete_projectuser", None)])
        )
        user = UserFactory()
        response = self.client.delete(
            reverse("ProjectUser-detail", args=[user.keycloak_id])
        )
        assert response.status_code == 404
        assert response.json()["error"] == "An error occured in Keycloak : None"
        assert ProjectUser.objects.filter(keycloak_id=user.keycloak_id).exists()

    def test_google_error_create_user(self):
        self.client.force_authenticate(
            user=UserFactory(
                permissions=[
                    ("accounts.add_projectuser", None),
                    ("organizations.change_organization", None),
                ]
            )
        )
        organization = OrganizationFactory(code="TEST_GOOGLE_SYNC")
        payload = {
            "people_id": faker.uuid4(),
            "email": f"{faker.uuid4()}@yopmail.com",
            "personal_email": f"{faker.uuid4()}@yopmail.com",
            "given_name": faker.first_name(),
            "family_name": faker.last_name(),
            "create_in_google": True,
            "roles_to_add": [organization.get_users().name],
        }
        with mock.patch(
            "services.google.interface.GoogleService.create_user_process",
            side_effect=self.mocked_google_error(),
        ):
            response = self.client.post(reverse("ProjectUser-list"), data=payload)
        assert response.status_code == 400
        assert (
            response.json()["error"]
            == "User was created but an error occured in Google : error reason"
        )
        user = ProjectUser.objects.filter(people_id=payload["people_id"])
        assert user.exists()
        keycloak_user = KeycloakService().get_user(user.get().keycloak_id)
        assert keycloak_user is not None

    def test_google_error_update_user(self):
        self.client.force_authenticate(
            user=UserFactory(permissions=[("accounts.change_projectuser", None)])
        )
        organization = OrganizationFactory(code="TEST_GOOGLE_SYNC")
        user = SeedUserFactory(
            email=f"{uuid.uuid4()}@{settings.GOOGLE_EMAIL_DOMAIN}",
            groups=[organization.get_users()],
        )
        payload = {
            "personal_email": f"{faker.uuid4()}@yopmail.com",
        }
        with mock.patch(
            "services.google.interface.GoogleService.update_user_process",
            side_effect=self.mocked_google_error(),
        ):
            response = self.client.patch(
                reverse("ProjectUser-detail", args=[user.keycloak_id]), data=payload
            )
        assert response.status_code == 400
        assert (
            response.json()["error"]
            == "User was updated but an error occured in Google : error reason"
        )
        user.refresh_from_db()
        assert user.personal_email == payload["personal_email"]
        keycloak_user = KeycloakService().get_user(user.keycloak_id)
        assert keycloak_user["email"] == user.personal_email

    def test_google_error_delete_user(self):
        self.client.force_authenticate(
            user=UserFactory(permissions=[("accounts.delete_projectuser", None)])
        )
        organization = OrganizationFactory(code="TEST_GOOGLE_SYNC")
        user = SeedUserFactory(groups=[organization.get_users()])
        with mock.patch(
            "services.google.interface.GoogleService.suspend_user_process",
            side_effect=self.mocked_google_error(),
        ):
            response = self.client.delete(
                reverse("ProjectUser-detail", args=[user.keycloak_id])
            )
        assert response.status_code == 400
        assert (
            response.json()["error"]
            == "User was deleted but an error occured in Google : error reason"
        )
        assert not ProjectUser.objects.filter(keycloak_id=user.keycloak_id).exists()
        with pytest.raises(KeycloakGetError):
            KeycloakService().get_user(user.keycloak_id)

    def test_google_error_create_people_group(self):
        self.client.force_authenticate(
            user=UserFactory(permissions=[("accounts.add_peoplegroup", None)])
        )
        organization = OrganizationFactory(code="TEST_GOOGLE_SYNC")
        payload = {
            "name": faker.word(),
            "description": faker.sentence(),
            "create_in_google": True,
            "organization": organization.pk,
        }
        with mock.patch(
            "services.google.interface.GoogleService.create_group_process",
            side_effect=self.mocked_google_error(),
        ):
            response = self.client.post(
                reverse("PeopleGroup-list", args=(organization.code,)), data=payload
            )
        assert response.status_code == 400
        assert response.json()["error"] == "An error occured in Google : error reason"
        assert not PeopleGroup.objects.filter(name=payload["name"]).exists()

    def test_google_error_update_people_group(self):
        self.client.force_authenticate(
            user=UserFactory(permissions=[("accounts.change_peoplegroup", None)])
        )
        organization = OrganizationFactory(code="TEST_GOOGLE_SYNC")
        group = PeopleGroupFactory(
            email=f"team.{uuid.uuid4()}@{settings.GOOGLE_EMAIL_DOMAIN}",
            publication_status=PeopleGroup.PublicationStatus.PUBLIC,
            organization=organization,
        )
        payload = {
            "description": faker.sentence(),
        }
        with mock.patch(
            "services.google.interface.GoogleService.update_group_process",
            side_effect=self.mocked_google_error(),
        ):
            response = self.client.patch(
                reverse("PeopleGroup-detail", args=(organization.code, group.pk)),
                data=payload,
            )
        assert response.status_code == 400
        assert response.json()["error"] == "An error occured in Google : error reason"
        group.refresh_from_db()
        assert group.description != payload["description"]

    def test_google_error_add_people_group_member(self):
        self.client.force_authenticate(
            user=UserFactory(permissions=[("accounts.change_peoplegroup", None)])
        )
        organization = OrganizationFactory(code="TEST_GOOGLE_SYNC")
        group = PeopleGroupFactory(
            email=f"team.{uuid.uuid4()}@{settings.GOOGLE_EMAIL_DOMAIN}",
            publication_status=PeopleGroup.PublicationStatus.PUBLIC,
            organization=organization,
        )
        user = SeedUserFactory(
            email=f"{uuid.uuid4()}@{settings.GOOGLE_EMAIL_DOMAIN}",
            groups=[organization.get_users()],
        )
        payload = {
            PeopleGroup.DefaultGroup.MEMBERS: [user.keycloak_id],
        }
        with mock.patch(
            "services.google.interface.GoogleService.update_group_process",
            side_effect=self.mocked_google_error(),
        ):
            response = self.client.post(
                reverse("PeopleGroup-add-member", args=(organization.code, group.pk)),
                data=payload,
            )
        assert response.status_code == 400
        assert response.json()["error"] == "An error occured in Google : error reason"
        assert not group.members.all().filter(pk=user.pk).exists()

    def test_google_error_remove_people_group_member(self):
        self.client.force_authenticate(
            user=UserFactory(permissions=[("accounts.change_peoplegroup", None)])
        )
        organization = OrganizationFactory(code="TEST_GOOGLE_SYNC")
        group = PeopleGroupFactory(
            email=f"team.{uuid.uuid4()}@{settings.GOOGLE_EMAIL_DOMAIN}",
            publication_status=PeopleGroup.PublicationStatus.PUBLIC,
            organization=organization,
        )
        user = SeedUserFactory(
            email=f"{uuid.uuid4()}@{settings.GOOGLE_EMAIL_DOMAIN}",
            groups=[organization.get_users(), group.get_members()],
        )
        payload = {
            "users": [user.keycloak_id],
        }
        with mock.patch(
            "services.google.interface.GoogleService.update_group_process",
            side_effect=self.mocked_google_error(),
        ):
            response = self.client.post(
                reverse(
                    "PeopleGroup-remove-member", args=(organization.code, group.pk)
                ),
                data=payload,
            )
        assert response.status_code == 400
        assert response.json()["error"] == "An error occured in Google : error reason"
        assert group.members.all().filter(pk=user.pk).exists()
