from unittest import TestCase

import pytest
from faker import Faker

from apps.accounts.factories import KeycloakAccountFactory
from apps.accounts.models import ProjectUser
from apps.organizations.factories import OrganizationFactory
from services.keycloak.interface import KeycloakService

faker = Faker()


@pytest.mark.django_db
class KeycloakServiceTestCase(TestCase):
    def test_import_user_with_groups(self):
        keycloak_user = KeycloakAccountFactory(
            groups=["45af436d-0fd9-462a-a7bd-0755c266b3b6"]
        )  # CRI users group id
        organization = OrganizationFactory(code="CRI")
        group = organization.get_users()
        user = KeycloakService.get_or_import_user(
            keycloak_user.keycloak_id, ProjectUser.objects.all()
        )
        assert user.keycloak_id == keycloak_user.keycloak_id
        assert user.people_id == keycloak_user.pid
        assert user.email == keycloak_user.username
        assert user.given_name == keycloak_user.first_name
        assert user.family_name == keycloak_user.last_name
        assert group in user.groups.all()
