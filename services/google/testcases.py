import json
from random import randint
from typing import List, Optional

from django.conf import settings
from googleapiclient.discovery import build
from googleapiclient.http import HttpMockSequence

from apps.commons.test import JwtAPITestCase
from services.google.models import GoogleAccount, GoogleGroup


class GoogleTestCase(JwtAPITestCase):
    @classmethod
    def google_side_effect(cls, responses):
        """
        This side effect is meant to be used with unittest mock. It will mock every call
        made to the Google API.
        - The desired responses and status codes must be provided in a list.
        - There must be a response for every call made to the API in the test.
        - The first element of the list will be the mocked response to the first call,
          the second for the second, etc.

        Arguments
        ---------

        - responses (list of tuples):
        [
            ({'status': response_status_code}, response_json),
            ({'status': response_status_code}, response_json)
        ]
        """

        def mocked_google_service(
            service: str = "admin", version: str = "directory_v1", admin: str = ""
        ):
            http = HttpMockSequence(responses)
            return build(service, version, http=http, developerKey="api_key")

        return mocked_google_service

    @classmethod
    def get_google_user_success(
        cls, google_user: Optional[GoogleAccount] = None, suspended: bool = False
    ):
        user = google_user.user if google_user else None
        content = json.dumps(
            {
                "kind": "admin#directory#user",
                "id": google_user.google_id if google_user else "",
                "etag": "etag",
                "primaryEmail": google_user.email if google_user else "",
                "name": {
                    "givenName": user.given_name if user else "",
                    "familyName": user.family_name if user else "",
                    "fullName": f"{user.given_name} {user.family_name}" if user else "",
                },
                "isAdmin": False,
                "isDelegatedAdmin": False,
                "lastLoginTime": "2022-11-14T13:55:46.000Z",
                "creationTime": "2022-02-07T15:16:01.000Z",
                "agreedToTerms": True,
                "suspended": suspended,
                "archived": False,
                "changePasswordAtNextLogin": False,
                "ipWhitelisted": False,
                "emails": [
                    {
                        "address": google_user.email if google_user else "",
                        "primary": True,
                    },
                    {
                        "address": (
                            google_user.email.replace(
                                settings.GOOGLE_EMAIL_DOMAIN,
                                settings.GOOGLE_EMAIL_ALIAS_DOMAIN,
                            )
                            if google_user
                            else ""
                        ),
                    },
                    (
                        {"address": f"{google_user.email}.test-google-a.com"}
                        if google_user
                        else ""
                    ),
                ],
                "languages": [{"languageCode": "en", "preference": "preferred"}],
                "aliases": (
                    [
                        google_user.email.replace(
                            settings.GOOGLE_EMAIL_DOMAIN,
                            settings.GOOGLE_EMAIL_ALIAS_DOMAIN,
                        )
                    ]
                    if google_user
                    else []
                ),
                "nonEditableAliases": (
                    [f"{google_user.email}.test-google-a.com"] if google_user else []
                ),
                "customerId": settings.GOOGLE_CUSTOMER_ID,  # nosec
                "orgUnitPath": google_user.organizational_unit if google_user else "",
                "isMailboxSetup": True,
                "isEnrolledIn2Sv": False,
                "isEnforcedIn2Sv": False,
                "includeInGlobalAddressList": True,
                "recoveryEmail": user.personal_email if user else "",
            }
        )
        return {"status": 200}, content

    @classmethod
    def get_google_user_error(cls, status_code: int = 404):
        content = json.dumps({"error": {"message": "Resource Not Found: userKey"}})
        return {"status": status_code}, content

    @classmethod
    def create_google_user_success(
        cls,
        given_name: str,
        family_name: str,
        organizational_unit: str,
        email_count: int = 0,
    ):
        if email_count == 0:
            email = f"{given_name}.{family_name}@{settings.GOOGLE_EMAIL_DOMAIN}"
        else:
            email = f"{given_name}.{family_name}.{email_count}@{settings.GOOGLE_EMAIL_DOMAIN}"
        content = json.dumps(
            {
                "kind": "admin#directory#user",
                "id": randint(100000000000000000000, 999999999999999999999),  # nosec
                "etag": "etag",
                "primaryEmail": email,
                "name": {"givenName": given_name, "familyName": family_name},
                "isAdmin": False,
                "isDelegatedAdmin": False,
                "creationTime": "2022-11-14T15:25:47.000Z",
                "changePasswordAtNextLogin": True,
                "customerId": settings.GOOGLE_CUSTOMER_ID,  # nosec
                "orgUnitPath": organizational_unit,
                "isMailboxSetup": False,
            }
        )
        return {"status": 201}, content

    @classmethod
    def create_google_user_error(cls, status_code: int = 409):
        content = json.dumps({"error": {"message": "Entity already exists"}})
        return {"status": status_code}, content

    @classmethod
    def update_google_user_success(
        cls, google_user: Optional[GoogleAccount] = None, suspended: bool = False
    ):
        return cls.get_google_user_success(google_user, suspended)

    @classmethod
    def update_google_user_error(cls, status_code: int = 404):
        content = json.dumps({"error": {"message": "Resource Not Found: userKey"}})
        return {"status": status_code}, content

    @classmethod
    def add_user_alias_success(cls):
        content = {
            "kind": "admin#directory#alias",
            "id": "103807802848557555696",
            "etag": "etag",
            "alias": f"alias@{settings.GOOGLE_EMAIL_ALIAS_DOMAIN}",
        }
        return {"status": 200}, json.dumps(content)

    @classmethod
    def add_user_alias_error(cls, status_code: int = 409):
        content = json.dumps({"error": {"message": "Entity already exists"}})
        return {"status": status_code}, content

    @classmethod
    def create_google_group_success(cls, email: str = "", name: str = ""):
        content = {
            "kind": "admin#directory#group",
            "id": randint(100000000000000000000, 999999999999999999999),  # nosec
            "etag": "etag",
            "email": email,
            "name": name,
            "directMembersCount": "1",
            "description": "description",
            "adminCreated": True,
            "aliases": [f"{email.split('@')[0]}@{settings.GOOGLE_EMAIL_ALIAS_DOMAIN}"],
            "nonEditableAliases": [
                f"{email.split('@')[0]}@alias.org.test-google-a.com"
            ],
        }
        return {"status": 201}, json.dumps(content)

    @classmethod
    def create_google_group_error(cls, status_code: int = 409):
        content = json.dumps({"error": {"message": "Entity already exists"}})
        return {"status": status_code}, content

    @classmethod
    def get_google_group_success(cls, google_group: Optional[GoogleGroup] = None):
        content = {
            "kind": "admin#directory#group",
            "id": google_group.google_id if google_group else "",
            "etag": "",
            "email": google_group.email if google_group else "",
            "name": google_group.people_group.name if google_group else "",
            "directMembersCount": "1",
            "description": "description",
            "adminCreated": True,
            "aliases": (
                [
                    f"{google_group.email.split('@')[0]}@{settings.GOOGLE_EMAIL_ALIAS_DOMAIN}"
                ]
                if google_group
                else []
            ),
            "nonEditableAliases": (
                [f"{google_group.email.split('@')[0]}@alias.org.test-google-a.com"]
                if google_group
                else []
            ),
        }
        return {"status": 200}, json.dumps(content)

    @classmethod
    def get_google_group_error(cls, status_code: int = 404):
        content = json.dumps({"error": {"message": "Resource Not Found: groupKey"}})
        return {"status": status_code}, content

    @classmethod
    def list_google_groups_success(
        cls, google_groups: List[GoogleGroup], has_next_page: bool = False
    ):
        content = {
            "kind": "admin#directory#groups",
            "etag": "etag",
            "groups": [
                json.loads(cls.get_google_group_success(google_group)[1])
                for google_group in google_groups
            ],
        }
        if has_next_page:
            content["nextPageToken"] = "token"  # nosec
        return {"status": 200}, json.dumps(content)

    @classmethod
    def list_google_groups_error(cls, status_code: int = 404):
        content = json.dumps({"error": {"message": "Resource Not Found: userKey"}})
        return {"status": status_code}, content

    @classmethod
    def add_user_to_group_success(cls, google_user: Optional[GoogleAccount] = None):
        content = json.dumps(
            {
                "kind": "admin#directory#group",
                "id": google_user.google_id if google_user else "",
                "email": google_user.email if google_user else "",
                "role": "MEMBER",
                "type": "USER",
                "status": "ACTIVE",
                "delivery_settings": "ALL_MAIL",
            }
        )
        return {"status": 200}, content

    @classmethod
    def list_group_members_success(
        cls, google_users: List[GoogleAccount], has_next_page: bool = False
    ):
        content = {
            "kind": "admin#directory#members",
            "etag": "etag",
            "members": [
                {
                    "kind": "admin#directory#member",
                    "etag": "etag",
                    "id": google_user.google_id,
                    "email": google_user.email,
                    "role": "MEMBER",
                    "type": "USER",
                    "status": "ACTIVE",
                    "delivery_settings": "ALL_MAIL",
                }
                for google_user in google_users
            ],
        }
        if has_next_page:
            content["nextPageToken"] = "token"
        return {"status": 200}, json.dumps(content)

    @classmethod
    def list_group_members_error(cls, status_code: int = 404):
        content = json.dumps({"error": {"message": "Resource Not Found: groupKey"}})
        return {"status": status_code}, content

    @classmethod
    def update_google_group_success(cls, google_group: Optional[GoogleGroup] = None):
        content = json.loads(cls.get_google_group_success(google_group)[1])
        return {"status": 200}, json.dumps(content)

    @classmethod
    def update_google_group_error(cls, status_code: int = 404):
        content = json.dumps({"error": {"message": "Resource Not Found: groupKey"}})
        return {"status": status_code}, content

    @classmethod
    def add_group_alias_success(cls, google_group: Optional[GoogleGroup] = None):
        content = {
            "kind": "admin#directory#alias",
            "id": google_group.google_id if google_group else "id",
            "etag": "etag",
            "alias": f"alias@{settings.GOOGLE_EMAIL_ALIAS_DOMAIN}",
        }
        return {"status": 200}, json.dumps(content)

    @classmethod
    def add_group_alias_error(cls, status_code: int = 409):
        content = json.dumps({"error": {"message": "Entity already exists"}})
        return {"status": status_code}, content

    @classmethod
    def add_user_to_group_error(cls, status_code: int = 409):
        content = json.dumps({"error": {"message": "Member already exists"}})
        return {"status": status_code}, content

    @classmethod
    def remove_user_from_group_success(cls):
        return {"status": 200}, json.dumps("")

    @classmethod
    def remove_user_from_group_error(cls, status_code: int = 404):
        content = json.dumps({"error": {"message": "Resource Not Found: memberKey"}})
        return {"status": status_code}, content
