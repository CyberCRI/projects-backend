import uuid

from django.urls import reverse
from faker import Faker
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.accounts.models import ProjectUser
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase
from apps.projects.factories import ProjectFactory
from apps.projects.models import Project
from services.keycloak.interface import KeycloakService

faker = Faker()


class KeycloakRelatedFieldTestCase(JwtAPITestCase):
    def test_import_user_from_keycloak(self):
        keycloak_payload = {
            "email": faker.email(),
            "username": faker.email(),
            "enabled": True,
            "firstName": faker.first_name(),
            "lastName": faker.last_name(),
        }
        keycloak_id = KeycloakService._create_user(keycloak_payload)

        user = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(user)
        project = ProjectFactory()
        payload = {
            Project.DefaultGroup.MEMBERS: [keycloak_id],
        }
        response = self.client.post(
            reverse("Project-add-member", args=(project.id,)), data=payload
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        user = ProjectUser.objects.get(keycloak_account__keycloak_id=keycloak_id)
        assert str(user.keycloak_id) == str(keycloak_payload["keycloak_id"])
        assert user.email == keycloak_payload["username"]
        assert user.given_name == keycloak_payload["first_name"]
        assert user.family_name == keycloak_payload["last_name"]

    def test_user_not_found_in_keycloak(self):
        user = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(user)
        project = ProjectFactory()
        payload = {
            Project.DefaultGroup.MEMBERS: [uuid.uuid4()],
        }
        response = self.client.post(
            reverse("Project-add-member", args=(project.id,)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
