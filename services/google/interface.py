import re
import time
import unicodedata
import uuid
from typing import TYPE_CHECKING

from django.conf import settings
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from apps.accounts.models import PeopleGroup, ProjectUser
from services.google.exceptions import GoogleGroupEmailUnavailable

if TYPE_CHECKING:
    from .models import GoogleAccount, GoogleGroup


class GoogleService:
    """
    A service to interact with the Google API.
    """

    _service = None

    @classmethod
    def service(cls):
        if cls._service is None:
            scopes = [
                "https://www.googleapis.com/auth/admin.directory.user",
                "https://www.googleapis.com/auth/admin.directory.group.member",
                "https://www.googleapis.com/auth/admin.directory.group",
                "https://www.googleapis.com/auth/admin.directory.orgunit",
                "https://www.googleapis.com/auth/admin.directory.user.alias",
                "https://www.googleapis.com/auth/apps.groups.settings",
            ]
            credentials = service_account.Credentials.from_service_account_info(
                settings.GOOGLE_CREDENTIALS, scopes=scopes
            )
            delegated_credentials = credentials.with_subject(
                settings.GOOGLE_SERVICE_ACCOUNT_EMAIL
            )
            cls._service = build(
                serviceName=settings.GOOGLE_SERVICE_NAME,
                version=settings.GOOGLE_SERVICE_VERSION,
                credentials=delegated_credentials,
            )
        return cls._service

    @staticmethod
    def text_to_ascii(text):
        """Convert a text to ASCII."""
        text = unicodedata.normalize("NFD", text.lower())
        text = text.encode("ascii", "ignore")
        text = text.decode("utf-8")
        text = str(text)
        return re.sub(r"[ _'-]", "", text)

    @classmethod
    def _get_user(cls, user_key: str):
        """
        Get a Google user from an email address.

        Args:
            - email (str): The email address of the user in Google.

        Returns:
            - A Google user.
        """
        try:
            return cls.service().users().get(userKey=user_key).execute()
        except HttpError as e:
            if e.status_code == 404:
                return None
            raise e

    @classmethod
    def get_user_by_email(cls, email: str, max_retries: int = 1):
        """
        Get a Google user from an email address.
        This method uses a retry mechanism because Google returns 404 errors for a
        few seconds after a new account is created.

        Args:
            - email (str): The email address of the user in Google.
            - max_retries (int): The maximum number of retries.

        Returns:
            - A Google user.
        """
        if (
            settings.GOOGLE_EMAIL_DOMAIN not in email
            and settings.GOOGLE_EMAIL_ALIAS_DOMAIN not in email
        ):
            return None
        for i in range(max_retries):
            user = cls._get_user(email)
            if user:
                return user
            if i < max_retries - 1:
                time.sleep(2)
        return None

    @classmethod
    def get_user_by_id(cls, google_id: str, max_retries: int = 1):
        """
        Get a Google user from an id.
        This method uses a retry mechanism because Google returns 404 errors for a
        few seconds after a new account is created.

        Args:
            - google_id (str): The id of the user in Google.
            - max_retries (int): The maximum number of retries.

        Returns:
            - A Google user.
        """
        for i in range(max_retries):
            user = cls._get_user(google_id)
            if user:
                return user
            if i < max_retries - 1:
                time.sleep(2)
        return None

    @classmethod
    def create_user(cls, user: ProjectUser, organizational_unit: str):
        """
        Create a Google user.

        Args:
            - user (ProjectUser): The user to create.
            - organizational_unit (str): The main group of the user.

        Returns:
            - A Google user.
        """
        username = cls.text_to_ascii(f"{user.given_name}.{user.family_name}")
        if settings.GOOGLE_EMAIL_PREFIX:
            username = f"{settings.GOOGLE_EMAIL_PREFIX}.{username}"
        email_address = f"{username}@{settings.GOOGLE_EMAIL_DOMAIN}"
        google_user = cls.get_user_by_email(email_address)
        same_address_count = 0
        while google_user:
            same_address_count += 1
            email_address = (
                f"{username}.{same_address_count}@{settings.GOOGLE_EMAIL_DOMAIN}"
            )
            google_user = cls.get_user_by_email(email_address)

        google_data = {
            "primaryEmail": email_address,
            "name": {
                "givenName": user.given_name,
                "familyName": user.family_name,
            },
            "changePasswordAtNextLogin": True,
            "password": str(uuid.uuid4().hex + uuid.uuid4().hex),
            "orgUnitPath": organizational_unit,
        }

        return cls.service().users().insert(body=google_data).execute()

    @classmethod
    def update_user(cls, google_account: "GoogleAccount"):
        body = {
            "name": {
                "givenName": google_account.user.given_name,
                "familyName": google_account.user.family_name,
            },
            "orgUnitPath": google_account.organizational_unit,
        }
        return (
            cls.service()
            .users()
            .update(
                userKey=google_account.google_id,
                body=body,
            )
            .execute()
        )

    @classmethod
    def suspend_user(cls, google_account: "GoogleAccount"):
        cls.service().users().update(
            userKey=google_account.google_id,
            body={
                "suspended": True,
                "suspensionReason": "Suspended by LPI Projects",
                "includeInGlobalAddressList": False,
            },
        ).execute()

    @classmethod
    def delete_user(cls, google_account: "GoogleAccount"):
        cls.service().users().delete(userKey=google_account.google_id).execute()

    @classmethod
    def add_user_alias(cls, google_account: "GoogleAccount", alias: str = ""):
        if not alias:
            alias = google_account.email.replace(
                settings.GOOGLE_EMAIL_DOMAIN, settings.GOOGLE_EMAIL_ALIAS_DOMAIN
            )
        cls.service().users().aliases().insert(
            userKey=google_account.google_id, body={"alias": alias}
        ).execute()

    @classmethod
    def get_user_groups(cls, google_account: "GoogleAccount"):
        response = (
            cls.service().groups().list(userKey=google_account.google_id).execute()
        )
        return response.get("groups", [])

    @classmethod
    def _get_group(cls, email: str):
        try:
            return cls.service().groups().get(groupKey=email).execute()
        except HttpError as e:
            if e.status_code == 404:
                return None
            raise e

    @classmethod
    def get_group_by_email(cls, email: str, max_retries: int = 1):
        if (
            settings.GOOGLE_EMAIL_DOMAIN not in email
            and settings.GOOGLE_EMAIL_ALIAS_DOMAIN not in email
        ):
            return None
        for i in range(max_retries):
            group = cls._get_group(email)
            if group:
                return group
            if i < max_retries - 1:
                time.sleep(2)
        return None

    @classmethod
    def get_group_by_id(cls, google_id: str, max_retries: int = 1):
        for i in range(max_retries):
            group = cls._get_group(google_id)
            if group:
                return group
            if i < max_retries - 1:
                time.sleep(2)
        return None

    @classmethod
    def get_groups(cls):
        groups = []
        request = cls.service().groups().list(customer=settings.GOOGLE_CUSTOMER_ID)
        while request is not None:
            response = request.execute()
            groups += response.get("groups", [])
            request = cls.service().groups().list_next(request, response)
        return groups

    @classmethod
    def create_group(cls, group: PeopleGroup):
        if group.email:
            google_group = cls.get_group_by_email(group.email)
            if (
                google_group is not None
                and PeopleGroup.objects.filter(google_group__email=group.email).exists()
            ):
                raise GoogleGroupEmailUnavailable
            email = group.email
        else:
            username = cls.text_to_ascii(f"team.{group.name}")
            if settings.GOOGLE_EMAIL_PREFIX:
                username = f"{settings.GOOGLE_EMAIL_PREFIX}.{username}"
            email = f"{username}@{settings.GOOGLE_EMAIL_DOMAIN}"
            google_group = cls.get_group_by_email(email)
            same_address_count = 0
            while google_group:
                same_address_count += 1
                email = (
                    f"{username}.{same_address_count}@{settings.GOOGLE_EMAIL_DOMAIN}"
                )
                google_group = cls.get_group_by_email(email)

        body = {
            "adminCreated": True,
            "email": email,
            "description": "",
            "kind": "admin#directory#group",
            "name": group.name,
        }
        return cls.service().groups().insert(body=body).execute()

    @classmethod
    def add_group_alias(cls, google_group: "GoogleGroup", alias: str = ""):
        if not alias:
            alias = google_group.email.replace(
                settings.GOOGLE_EMAIL_DOMAIN, settings.GOOGLE_EMAIL_ALIAS_DOMAIN
            )
        cls.service().groups().aliases().insert(
            groupKey=google_group.google_id, body={"alias": alias}
        ).execute()

    @classmethod
    def update_group(cls, google_group: "GoogleGroup"):
        body = {"name": google_group.people_group.name}
        return (
            cls.service()
            .groups()
            .update(groupKey=google_group.google_id, body=body)
            .execute()
        )

    @classmethod
    def delete_group(cls, google_group: "GoogleGroup"):
        cls.service().groups().delete(groupKey=google_group.google_id).execute()

    @classmethod
    def get_group_members(cls, google_group: "GoogleGroup"):
        members = []
        request = cls.service().members().list(groupKey=google_group.google_id)
        while request is not None:
            response = request.execute()
            members += response.get("members", [])
            request = cls.service().members().list_next(request, response)
        return members

    @classmethod
    def add_user_to_group(
        cls, google_account: "GoogleAccount", google_group: "GoogleGroup"
    ):
        body = {
            "email": google_account.email,
            "id": google_account.google_id,
            "delivery_settings": "ALL_MAIL",
            "role": "MEMBER",
            "type": "USER",
            "status": "ACTIVE",
            "kind": "admin#directory#group",
        }
        return (
            cls.service()
            .members()
            .insert(groupKey=google_group.google_id, body=body)
            .execute()
        )

    @classmethod
    def remove_user_from_group(
        cls, google_account: "GoogleAccount", google_group: "GoogleGroup"
    ):
        return (
            cls.service()
            .members()
            .delete(groupKey=google_group.google_id, memberKey=google_account.google_id)
            .execute()
        )

    @classmethod
    def get_org_units(cls):
        org_units = (
            cls.service()
            .orgunits()
            .list(customerId=settings.GOOGLE_CUSTOMER_ID, orgUnitPath="", type="all")
            .execute()
        )
        return [org_unit["orgUnitPath"] for org_unit in org_units["organizationUnits"]]
