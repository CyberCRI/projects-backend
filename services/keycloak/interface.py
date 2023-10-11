import logging
from typing import Dict, List, Union

from django.conf import settings
from django.db.models import QuerySet
from django.http import Http404
from rest_framework import status

from apps.accounts.models import ProjectUser
from apps.accounts.utils import get_superadmins_group
from apps.organizations.models import Organization
from keycloak import KeycloakAdmin, exceptions

logger = logging.getLogger(__name__)


class KeycloakService:
    """
    Keycloak API service.
    """

    @classmethod
    def service(cls):
        return KeycloakAdmin(
            server_url=settings.KEYCLOAK_SERVER_URL,
            realm_name=settings.KEYCLOAK_REALM,
            client_id=settings.KEYCLOAK_CLIENT_ID,
            client_secret_key=settings.KEYCLOAK_CLIENT_SECRET,
            verify=True,
        )

    @staticmethod
    def get_token_for_user(username, password):
        try:
            service = KeycloakAdmin(
                server_url=settings.KEYCLOAK_SERVER_URL,
                username=username,
                password=password,
                realm_name=settings.KEYCLOAK_REALM,
                user_realm_name=settings.KEYCLOAK_REALM,
                verify=True,
            )
            return status.HTTP_200_OK, service.token
        except exceptions.KeycloakAuthenticationError:
            return status.HTTP_401_UNAUTHORIZED, {"error": "Invalid user credentials"}

    @classmethod
    def get_user(cls, keycloak_id: str):
        return cls.service().get_user(keycloak_id)

    @classmethod
    def get_users(cls):
        return cls.service().get_users({})

    @classmethod
    def _create_user(cls, keycloak_data: Dict[str, Union[str, bool]]):
        """
        keycloak_data should respect the following structure :
        keycloak_data = {
            "email": "foo.bar@personalmail.com",
            "username": "foo.bar@primaryemail.com",
            "firstName": "foo",
            "lastName": "bar",
        }
        """
        return cls.service().create_user(payload=keycloak_data, exist_ok=False)

    @classmethod
    def create_user(
        cls,
        request_data: Dict[str, Union[str, bool]],
        redirect_organization_code: str = "DEFAULT",
    ):
        payload = {
            "enabled": True,
            "emailVerified": False,
            "email": request_data.get("personal_email", request_data["email"]),
            "username": request_data["email"],
            "firstName": request_data["given_name"],
            "lastName": request_data["family_name"],
            "attributes": {
                "locale": [request_data.get("language", "en")],
            },
        }
        password = request_data.get("password", None)
        required_actions = ["VERIFY_EMAIL"]
        if password:
            payload["credentials"] = [{"type": "password", "value": password}]
        else:
            required_actions.append("UPDATE_PASSWORD")
        keycloak_id = cls._create_user(payload)
        cls.send_required_actions_email(
            keycloak_id, required_actions, redirect_organization_code
        )
        return keycloak_id

    @classmethod
    def send_required_actions_email(
        cls,
        keycloak_id: str,
        required_actions: List[str],
        redirect_organization_code: str = "DEFAULT",
    ) -> bool:
        keycloak_admin = cls.service()
        keycloak_user = cls.get_user(keycloak_id)
        required_actions = list(
            set(required_actions + keycloak_user.get("requiredActions", []))
        )
        if len(required_actions) == 0:
            return False
        update_account_args = {
            "user_id": keycloak_id,
            "payload": required_actions,
            "client_id": "admin-cli",
        }
        organization = Organization.objects.filter(code=redirect_organization_code)
        keycloak_attributes = keycloak_user.get("attributes", {})
        if organization.exists():
            organization = organization.get()
            keycloak_attributes = {
                **keycloak_attributes,
                "keycloakId": [keycloak_id],
                "emailOrganizationCode": [organization.code],
                "emailOrganizationName": [organization.name],
                "emailOrganizationLogo": [
                    f"{organization.website_url}/v1/organization/{organization.code}/logo/{organization.logo_image.id}/"
                ],
            }
            update_account_args["redirect_uri"] = organization.website_url

        payload = {
            "requiredActions": required_actions,
            "attributes": keycloak_attributes,
        }
        cls._update_user(keycloak_id=keycloak_id, payload=payload)
        keycloak_admin.send_update_account(**update_account_args)
        return True

    @classmethod
    def get_reset_password_link(cls):
        keycloak_admin = cls.service()
        return keycloak_admin.get_reset_password_link()

    @classmethod
    def import_user(cls, keycloak_id: str) -> ProjectUser:
        keycloak_admin = cls.service()
        try:
            keycloak_user = keycloak_admin.get_user(keycloak_id)
        except exceptions.KeycloakGetError:
            raise Http404()
        people_id = keycloak_user.get("attributes", {}).get("pid", [None])[0]
        if people_id and ProjectUser.objects.filter(people_id=people_id).exists():
            people_id = None
        user = ProjectUser.objects.create(
            keycloak_id=keycloak_user.get("id", ""),
            people_id=people_id,
            email=keycloak_user.get("username", ""),
            personal_email=keycloak_user.get("email", ""),
            given_name=keycloak_user.get("firstName", ""),
            family_name=keycloak_user.get("lastName", ""),
        )
        return cls.sync_groups_from_keycloak(user)

    @classmethod
    def get_or_import_user(
        cls, keycloak_id: str, queryset: QuerySet[ProjectUser]
    ) -> ProjectUser:
        user = queryset.filter(keycloak_id=keycloak_id)
        if user.exists():
            return user.get()
        return cls.import_user(keycloak_id)

    @classmethod
    def sync_groups_from_keycloak(cls, user: ProjectUser) -> ProjectUser:
        keycloak_groups = cls.get_user_groups(user.keycloak_id)
        for keycloak_group in keycloak_groups:
            path = keycloak_group.get("path")
            if path == "/projects/administrators":
                user.groups.add(get_superadmins_group())
            else:
                split_path = path.split("/")
                name = {
                    "users": Organization.DefaultGroup.USERS,
                    "administrators": Organization.DefaultGroup.ADMINS,
                }.get(split_path[-1])
                if not name:
                    continue
                organization = Organization.objects.get(code=split_path[-2])
                organizations_group = organization.get_or_create_group(name)
                user.groups.add(organizations_group)
        return user

    @classmethod
    def get_user_groups(cls, keycloak_id: str) -> List[Dict[str, str]]:
        return cls.service().get_user_groups(keycloak_id)

    @classmethod
    def add_user_to_keycloak_group(cls, keycloak_id: str, group_id: str):
        return cls.service().group_user_add(keycloak_id, group_id)

    @classmethod
    def get_superadmins(cls) -> list:
        keycloak_admin = cls.service()
        group = keycloak_admin.get_group_by_path(
            path="/projects/administrators", search_in_subgroups=True
        )
        if not group:
            return []
        return keycloak_admin.get_group_members(
            group.get("id", ""), {"briefRepresentation": True, "max": -1}
        )

    @classmethod
    def get_members_from_organization(cls, code: str, subgroup: str) -> list:
        keycloak_admin = cls.service()
        group = keycloak_admin.get_group_by_path(
            path=f"/projects/portals/{code}/{subgroup}", search_in_subgroups=True
        )
        if not group:
            return []
        return keycloak_admin.get_group_members(
            group.get("id", ""), {"briefRepresentation": True, "max": -1}
        )

    @classmethod
    def _update_user(cls, keycloak_id: str, payload: dict):
        cls.service().update_user(user_id=keycloak_id, payload=payload)

    @classmethod
    def update_user(cls, user: ProjectUser):
        keycloak_user = cls.get_user(user.keycloak_id)
        payload = {
            "email": user.personal_email if user.personal_email else user.email,
            "username": user.email,
            "firstName": user.given_name,
            "lastName": user.family_name,
            "attributes": {
                **keycloak_user.get("attributes", {}),
                "locale": [user.language],
            },
        }
        return cls._update_user(keycloak_id=user.keycloak_id, payload=payload)

    @classmethod
    def delete_user(cls, user: ProjectUser):
        keycloak_admin = cls.service()
        try:
            keycloak_admin.get_user(user.keycloak_id)
            keycloak_admin.delete_user(user_id=user.keycloak_id)
        except exceptions.KeycloakGetError:
            logger.info(f"Deleted user {user.keycloak_id} does not exist in Keycloak")
