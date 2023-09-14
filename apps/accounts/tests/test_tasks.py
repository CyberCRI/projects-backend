from apps.accounts.factories import KeycloakAccountFactory
from apps.accounts.models import ProjectUser
from apps.accounts.tasks import _import_users_from_keycloak
from apps.commons.test import JwtAPITestCase
from apps.organizations.factories import OrganizationFactory


class ImportKeycloakUsersTaskTestCase(JwtAPITestCase):
    def test_import_users_from_keycloak(self):
        organization = OrganizationFactory(code="CRI")
        user = KeycloakAccountFactory(
            groups=["45af436d-0fd9-462a-a7bd-0755c266b3b6"]
        )  # CRI users
        admin = KeycloakAccountFactory(
            groups=["81f9184e-4764-4c67-83f8-db2010e2d0cc"]
        )  # CRI admins
        _import_users_from_keycloak()
        user = ProjectUser.objects.filter(keycloak_id=user.keycloak_id)
        admin = ProjectUser.objects.filter(keycloak_id=admin.keycloak_id)

        assert user.exists() is True
        assert admin.exists() is True

        user = user.get()
        admin = admin.get()
        users = organization.get_users()
        admins = organization.get_admins()

        assert users in user.groups.all()
        assert admins in admin.groups.all()
        assert user in organization.get_all_members().all()
        assert admin in organization.get_all_members().all()
