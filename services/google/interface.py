import re
import time
import unicodedata
import uuid

from django.conf import settings
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from apps.accounts.models import PeopleGroup, ProjectUser


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
    def _get_user(cls, email: str):
        """
        Get a Google user from an email address.

        Args:
            - email (str): The email address of the user in Google.

        Returns:
            - A Google user.
        """
        try:
            return cls.service().users().get(userKey=email).execute()
        except HttpError as e:
            if e.status_code == 404:
                return None
            raise e

    @classmethod
    def get_user(cls, email: str, max_retries: int = 1):
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
        for _ in range(max_retries):
            user = cls._get_user(email)
            if user:
                return user
            time.sleep(2)
        return None

    @classmethod
    def create_user(cls, user: ProjectUser, main_group: str):
        """
        Create a Google user.

        Args:
            - firstname (str): The first name of the user.
            - lastname (str): The last name of the user.
            - main_group (str): The main group of the user.
            - email_domain (str): The email domain of the user.

        Returns:
            - A Google user.
        """
        username = cls.text_to_ascii(f"{user.given_name}.{user.family_name}")
        if settings.GOOGLE_EMAIL_PREFIX:
            username = f"{settings.GOOGLE_EMAIL_PREFIX}.{username}"
        email_address = f"{username}@{settings.GOOGLE_EMAIL_DOMAIN}"
        google_user = cls.get_user(email_address)
        same_address_count = 0
        while google_user:
            same_address_count += 1
            email_address = (
                f"{username}.{same_address_count}@{settings.GOOGLE_EMAIL_DOMAIN}"
            )
            google_user = cls.get_user(email_address)

        google_data = {
            "primaryEmail": email_address,
            "name": {
                "givenName": user.given_name,
                "familyName": user.family_name,
            },
            "changePasswordAtNextLogin": True,
            "password": str(uuid.uuid4().hex + uuid.uuid4().hex),
            "orgUnitPath": f"/CRI/{main_group}",
        }

        return cls.service().users().insert(body=google_data).execute()

    @classmethod
    def _update_user(cls, user: ProjectUser, google_user: dict, **kwargs):
        body = {
            **google_user,
            **kwargs,
            "name": {
                "givenName": user.given_name,
                "familyName": user.family_name,
            },
        }
        cls.service().users().update(
            userKey=google_user["id"],
            body=body,
        ).execute()

    @classmethod
    def update_user(cls, user: ProjectUser, **kwargs):
        google_user = cls.get_user(user.email)
        if google_user:
            cls._update_user(user, google_user, **kwargs)

    @classmethod
    def suspend_user(cls, user: ProjectUser):
        google_user = cls.get_user(user.email)
        if google_user:
            cls.service().users().update(
                userKey=google_user["id"],
                body={
                    "suspended": True,
                    "suspensionReason": "Suspended by LPI Projects",
                    "includeInGlobalAddressList": False,
                },
            ).execute()

    @classmethod
    def delete_user(cls, user: ProjectUser):
        google_user = cls.get_user(user.email)
        if google_user:
            cls.service().users().delete(userKey=google_user["id"]).execute()

    @classmethod
    def _add_user_alias(cls, google_user: dict, alias: str = ""):
        if not alias:
            email = google_user["primaryEmail"]
            alias = email.replace(
                settings.GOOGLE_EMAIL_DOMAIN, settings.GOOGLE_EMAIL_ALIAS_DOMAIN
            )
        cls.service().users().aliases().insert(
            userKey=google_user["id"], body={"alias": alias}
        ).execute()

    @classmethod
    def add_user_alias(cls, user: ProjectUser, alias: str = ""):
        google_user = cls.get_user(user.email)
        if google_user:
            cls._add_user_alias(google_user, alias)

    @classmethod
    def _get_user_groups(cls, google_user: dict):
        response = cls.service().groups().list(userKey=google_user["id"]).execute()
        return response.get("groups", [])

    @classmethod
    def get_user_groups(cls, user: ProjectUser):
        google_user = cls.get_user(user.email)
        if google_user:
            return cls._get_user_groups(google_user)
        return []

    @classmethod
    def _get_group(cls, email: str):
        try:
            return cls.service().groups().get(groupKey=email).execute()
        except HttpError as e:
            if e.status_code == 404:
                return None
            raise e

    @classmethod
    def get_group(cls, email: str, max_retries: int = 1):
        if (
            settings.GOOGLE_EMAIL_DOMAIN not in email
            and settings.GOOGLE_EMAIL_ALIAS_DOMAIN not in email
        ):
            return None
        for _ in range(max_retries):
            group = cls._get_group(email)
            if group:
                return group
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
            email = group.email
        else:
            username = cls.text_to_ascii(f"team.{group.name}")
            if settings.GOOGLE_EMAIL_PREFIX:
                username = f"{settings.GOOGLE_EMAIL_PREFIX}.{username}"
            email = f"{username}@{settings.GOOGLE_EMAIL_DOMAIN}"
            google_group = cls.get_group(email)
            same_address_count = 0
            while google_group:
                same_address_count += 1
                email = (
                    f"{username}.{same_address_count}@{settings.GOOGLE_EMAIL_DOMAIN}"
                )
                google_group = cls.get_group(email)

        body = {
            "adminCreated": True,
            "email": email,
            "description": "",
            "kind": "admin#directory#group",
            "name": group.name,
        }
        return cls.service().groups().insert(body=body).execute()

    @classmethod
    def _update_group(cls, group: PeopleGroup, google_group: dict, **kwargs):
        body = {"name": group.name, **kwargs}
        return (
            cls.service()
            .groups()
            .update(groupKey=google_group["id"], body=body)
            .execute()
        )

    @classmethod
    def update_group(cls, group: PeopleGroup, **kwargs):
        google_group = cls.get_group(group.email)
        if google_group:
            cls._update_group(group, google_group, **kwargs)

    @classmethod
    def _delete_group(cls, email: str):
        return cls.service().groups().delete(groupKey=email).execute()

    @classmethod
    def delete_group(cls, group: PeopleGroup):
        google_group = cls.get_group(group.email)
        if google_group:
            cls._delete_group(group.email)

    @classmethod
    def _get_group_members(cls, email: str):
        members = []
        request = cls.service().members().list(groupKey=email)
        while request is not None:
            response = request.execute()
            members += response.get("members", [])
            request = cls.service().groups().list_next(request, response)
        return members

    @classmethod
    def get_group_members(cls, group: PeopleGroup):
        google_group = cls.get_group(group.email)
        if google_group:
            return cls._get_group_members(group.email)
        return []

    @classmethod
    def _add_user_to_group(cls, google_user: dict, google_group: dict):
        body = {
            "delivery_settings": "ALL_MAIL",
            "email": google_user["primaryEmail"],
            "etag": google_group["etag"],
            "id": google_user["id"],
            "role": "MEMBER",
            "type": "USER",
            "status": "ACTIVE",
            "kind": google_group["kind"],
        }
        return (
            cls.service()
            .members()
            .insert(groupKey=google_group["id"], body=body)
            .execute()
        )

    @classmethod
    def add_user_to_group(cls, user: ProjectUser, group: PeopleGroup):
        google_user = cls.get_user(user.email)
        google_group = cls.get_group(group.email)
        if google_user and google_group:
            cls._add_user_to_group(google_user, google_group)

    @classmethod
    def _remove_user_from_group(cls, google_user: dict, google_group: dict):
        return (
            cls.service()
            .members()
            .delete(groupKey=google_group["id"], memberKey=google_user["id"])
            .execute()
        )

    @classmethod
    def remove_user_from_group(cls, user: ProjectUser, group: PeopleGroup):
        google_user = cls.get_user(user.email)
        google_group = cls.get_group(group.email)

        if google_user and google_group:
            cls._remove_user_from_group(google_user, google_group)

    @classmethod
    def _sync_user_groups(cls, user: ProjectUser, google_user: dict):
        people_groups = PeopleGroup.objects.filter(
            organization__code=settings.GOOGLE_SYNCED_ORGANIZATION,
            groups__id__in=user.groups.values("id"),
        )
        google_groups = cls._get_user_groups(google_user)
        google_groups = [
            {
                **google_group,
                "emails": [
                    google_group["email"],
                    *google_group.get("aliases", [])
                ]
            }
            for google_group in google_groups
        ]
        people_groups_emails = list(
            filter(lambda x: x, [group.email for group in people_groups])
        )

        for google_group in [
            group
            for group in google_groups
            if (
                not any(email in people_groups_emails for email in group["emails"])
                and PeopleGroup.objects.filter(email=group["email"]).exists()
            )
        ]:
            cls._remove_user_from_group(google_user, google_group)

        google_groups_emails = [
            email
            for sublist in [group["emails"] for group in google_groups]
            for email in sublist
        ]
        for people_group in [
            group for group in people_groups if group.email not in google_groups_emails
        ]:
            google_group = cls.get_group(people_group.email)
            if google_group:
                cls._add_user_to_group(google_user, google_group)

    @classmethod
    def sync_user_groups(cls, user: ProjectUser):
        google_user = cls.get_user(user.email)
        if google_user:
            cls._sync_user_groups(user, google_user)

    @classmethod
    def _sync_group_members(cls, group: PeopleGroup, google_group: dict):
        google_users = cls._get_group_members(group.email)
        # TODO : Remove this when google is handled in db
        google_users = [
            {
                **google_user,
                "emails": [
                    google_user["email"],
                    *[
                        alias["alias"]
                        for alias in (
                            cls.service()
                            .users()
                            .aliases()
                            .list(userKey=google_user["id"])
                            .execute()
                            .get("aliases", [])
                        )
                    ]
                ]
            }
            for google_user in google_users
        ]
        projects_users_emails = list(
            filter(lambda x: x, [user.email for user in group.get_all_members()])
        )

        for google_user in [
            user
            for user in google_users
            if (
                not any(email in projects_users_emails for email in user["emails"])
                and ProjectUser.objects.filter(email=user["email"]).exists()
            )
        ]:
            cls._remove_user_from_group(google_user, google_group)

        google_users_emails = [
            email 
            for sublist in [user["emails"] for user in google_users]
            for email in sublist
        ]
        for projects_user in [
            user
            for user in group.get_all_members().filter()
            if (
                user.email not in google_users_emails
                and user.groups.filter(
                    organizations__code=settings.GOOGLE_SYNCED_ORGANIZATION
                ).exists()
            )
        ]:
            google_user = cls.get_user(projects_user.email)
            if google_user:
                cls._add_user_to_group(google_user, google_group)

    @classmethod
    def sync_group_members(cls, group: PeopleGroup):
        google_group = cls.get_group(group.email)
        if google_group:
            cls._sync_group_members(group, google_group)

    @classmethod
    def get_org_units(cls):
        org_units = (
            cls.service()
            .orgunits()
            .list(customerId=settings.GOOGLE_CUSTOMER_ID, orgUnitPath="CRI")
            .execute()
        )
        return [org_unit["name"] for org_unit in org_units["organizationUnits"]]
