import logging
from datetime import datetime
from typing import Dict, List, Optional, Union

from babel.dates import format_date, format_time
from django.conf import settings
from django.db import models
from django.db.models import QuerySet
from django.http import Http404
from keycloak.exceptions import (
    KeycloakAuthenticationError,
    KeycloakGetError,
    raise_error_from_response,
)
from rest_framework import status

from apps.accounts.models import ProjectUser
from apps.accounts.utils import get_superadmins_group
from apps.emailing.utils import render_message, send_email
from apps.organizations.models import Organization
from keycloak import KeycloakAdmin

logger = logging.getLogger(__name__)


class KeycloakService:
    """
    Keycloak API service.
    """

    EMAIL_CLIENT_ID = "admin-cli"

    class EmailType(models.TextChoices):
        """
        Types of emails sent to users.
        """

        INVITATION = "invitation"
        ADMIN_CREATED = "admin_created"
        FORCE_RESET_PASSWORD = "force_reset_password"
        RESET_PASSWORD = "reset_password"

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
        except KeycloakAuthenticationError:
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
    def create_user(cls, request_data: Dict[str, Union[str, bool]]):
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
        if password:
            payload["credentials"] = [{"type": "password", "value": password}]
            payload["requiredActions"] = ["VERIFY_EMAIL"]
        else:
            payload["requiredActions"] = ["UPDATE_PASSWORD", "VERIFY_EMAIL"]
        return cls._create_user(payload)

    @classmethod
    def get_user_execute_actions_link(
        cls,
        user: ProjectUser,
        email_type: str,
        actions: List[str],
        redirect_uri: str,
        lifespan: Optional[int] = None,
    ) -> str:
        """
        Get the link to execute actions on a user from the custom endpoint created in Keycloak.

        response example:
        {
            "lifespan": 43200,
            "email_type": "invitation",
            "link": "http://lpi-keycloak.org/realms/lp/login-actions/action-token?key=abcde",
            "expiration": 1701311686,
            "redirect_uri": "https://projects.learningplanetinstitute.org",
            "actions": ["UPDATE_PASSWORD", "VERIFY_EMAIL"],
            "client_id": "admin-cli"
        }
        """
        if settings.ENVIRONMENT == "test":
            return {}
        if email_type not in cls.EmailType.values:
            raise ValueError(f"Email type {email_type} is not valid")
        service = cls.service()
        url = f"realms/lp/custom/user/{user.keycloak_id}/execute-actions-token/"
        url += f"?client_id={cls.EMAIL_CLIENT_ID}"
        url += f"&email_type={email_type}"
        url += f"&actions={','.join(actions)}"
        url += f"&redirect_uri={redirect_uri}"
        url += f"&lifespan={lifespan}" if lifespan else ""
        data_raw = service.raw_get(url)
        return raise_error_from_response(data_raw, KeycloakGetError)

    @classmethod
    def format_execute_action_link_for_template(
        cls,
        link: Dict[str, Union[int, str]],
        user: ProjectUser,
        organization: Optional[Organization] = None,
    ) -> Dict[str, Union[int, str]]:
        """
        Format the link response from Keycloak to be used in an email template.
        """
        link["expiration_date"] = format_date(
            datetime.fromtimestamp(link["expiration"]).astimezone(),
            format="full",
            locale=user.language,
        )
        link["expiration_time"] = format_time(
            datetime.fromtimestamp(link["expiration"]).astimezone(),
            format="short",
            locale=user.language,
        )
        if organization:
            link["refresh_link"] = (
                f"{settings.PUBLIC_URL}"
                + f"/v1/user/{user.keycloak_id}/refresh-keycloak-actions-link"
                + f"/?organization={organization.code}"
                + f"&email_type={link['email_type']}"
            )
        return link

    @classmethod
    def send_email(
        cls,
        user: ProjectUser,
        email_type: str,
        actions: Optional[List[str]] = None,
        redirect_organization_code: str = "DEFAULT",
        lifespan: Optional[int] = None,
    ):
        """
        Send an email to a user to execute actions on his account.

        There are 3 types of emails:
            - INVITATION: sent when a user creates an account on the platform using an invitation link
            - ADMIN_CREATED: sent when an administrator creates an account for a user
            - RESET_PASSWORD: sent when a user wants to reset his password

        The email contains a link to execute actions on the user account.

        It also contains a link to ask for a new email if the user did not complete the actions on time.
        This will send the same type of email with all the actions currently required, even if some of them
        were not required at the time of the first email.

        Arguments:
            - user: the user to send the email to
            - email_type: the type of email to send
            - actions: the actions to execute on the user account
                - If none is provided, only the currently required actions retrieved from Keycloak will be used
                - if some actions are provided, they will be added to the currently required actions
            - redirect_organization_code: the code of the organization to redirect the user to after
                executing the actions
            - lifespan: the lifespan of the link to execute the actions, in seconds

        Returns:
            - True if the email was sent successfully
            - False if the email was not sent because no action was required
        """
        if email_type not in cls.EmailType.values:
            raise ValueError(f"Email type {email_type} is not valid")
        keycloak_user = cls.get_user(user.keycloak_id)
        if not actions:
            actions = keycloak_user.get("requiredActions", [])
        else:
            actions = list(set(actions + keycloak_user.get("requiredActions", [])))
            cls._update_user(
                keycloak_id=user.keycloak_id,
                payload={"requiredActions": actions},
            )
        if len(actions) == 0:
            return False
        organization = Organization.objects.get(code=redirect_organization_code)
        contact_email = user.personal_email if user.personal_email else user.email
        link = cls.get_user_execute_actions_link(
            user, email_type, actions, organization.website_url, lifespan
        )
        link = cls.format_execute_action_link_for_template(link, user, organization)
        subject, _ = render_message(
            f"{email_type}/object", user.language, user=user, organization=organization
        )
        text, html = render_message(
            f"{email_type}/mail",
            user.language,
            user=user,
            contact_email=contact_email,
            organization=organization,
            link=link,
        )
        send_email(subject, text, [contact_email], html_content=html)
        return True

    @classmethod
    def send_reset_password_email(cls, user: ProjectUser, redirect_uri: str):
        if not redirect_uri:
            raise ValueError("redirect_uri is required")
        try:
            keycloak_user = cls.get_user(user.keycloak_id)
        except KeycloakGetError:
            raise Http404()
        actions = list(
            set(["UPDATE_PASSWORD"] + keycloak_user.get("requiredActions", []))
        )
        contact_email = user.personal_email if user.personal_email else user.email
        link = cls.get_user_execute_actions_link(
            user, cls.EmailType.RESET_PASSWORD, actions, redirect_uri
        )
        link = cls.format_execute_action_link_for_template(link, user)
        subject, _ = render_message(
            f"{cls.EmailType.RESET_PASSWORD}/object", user.language, user=user
        )
        text, html = render_message(
            f"{cls.EmailType.RESET_PASSWORD}/mail",
            user.language,
            user=user,
            contact_email=contact_email,
            link=link,
        )
        send_email(subject, text, [contact_email], html_content=html)
        return True

    @classmethod
    def import_user(cls, keycloak_id: str) -> ProjectUser:
        keycloak_admin = cls.service()
        try:
            keycloak_user = keycloak_admin.get_user(keycloak_id)
        except KeycloakGetError:
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
        except KeycloakGetError:
            logger.info(f"Deleted user {user.keycloak_id} does not exist in Keycloak")
