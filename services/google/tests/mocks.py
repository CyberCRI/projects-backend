import json
from random import randint
from typing import Dict, List
from django.conf import settings

from googleapiclient.discovery import build
from googleapiclient.http import HttpMockSequence

from apps.accounts.models import ProjectUser, PeopleGroup
from apps.commons.test.testcases import JwtAPITestCase
from services.google.models import GoogleGroup


class GoogleTestCase(JwtAPITestCase):
    @staticmethod
    def google_side_effect(responses):
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


def get_google_user(user: ProjectUser):
    content = json.dumps(
        {
            "kind": "admin#directory#user",
            "id": user.google_account.id,
            "etag": "etag",
            "primaryEmail": user.google_account.email,
            "name": {
                "givenName": user.given_name,
                "familyName": user.family_name,
                "fullName": f"{user.given_name} {user.family_name}",
            },
            "isAdmin": False,
            "isDelegatedAdmin": False,
            "lastLoginTime": "2022-11-14T13:55:46.000Z",
            "creationTime": "2022-02-07T15:16:01.000Z",
            "agreedToTerms": True,
            "suspended": False,
            "archived": False,
            "changePasswordAtNextLogin": False,
            "ipWhitelisted": False,
            "emails": [
                {"address": user.google_account.email, "primary": True},
                {"address": user.google_account.email.replace(settings.GOOGLE_EMAIL_DOMAIN, settings.GOOGLE_EMAIL_ALIAS_DOMAIN)},
                {"address": f"{user.google_account.email}.test-google-a.com"},
            ],
            "languages": [{"languageCode": "en", "preference": "preferred"}],
            "aliases": [user.google_account.email.replace(settings.GOOGLE_EMAIL_DOMAIN, settings.GOOGLE_EMAIL_ALIAS_DOMAIN)],
            "nonEditableAliases": [f"{user.google_account.email}.test-google-a.com"],
            "customerId": settings.GOOGLE_CUSTOMER_ID,  # nosec
            "orgUnitPath": user.google_account.organizational_unit,
            "isMailboxSetup": True,
            "isEnrolledIn2Sv": False,
            "isEnforcedIn2Sv": False,
            "includeInGlobalAddressList": True,
            "recoveryEmail": user.personal_email,
        }
    )
    return {"status": 200}, content


def get_google_user_not_found():
    content = json.dumps({"error": {"message": "Resource Not Found: userKey"}})
    return {"status": 404}, content


def create_google_user_already_exist():
    content = json.dumps({"error": {"message": "Entity already exists"}})
    return {"status": 409}, content


def create_google_user(user: ProjectUser, primary_email: str):
    content = json.dumps(
        {
            "kind": "admin#directory#user",
            "id": randint(100000000000000000000, 999999999999999999999),  # nosec
            "etag": "etag",
            "primaryEmail": primary_email,
            "name": {"givenName": user.given_name, "familyName": user.family_name},
            "isAdmin": False,
            "isDelegatedAdmin": False,
            "creationTime": "2022-11-14T15:25:47.000Z",
            "changePasswordAtNextLogin": True,
            "customerId": settings.GOOGLE_CUSTOMER_ID,  # nosec
            "orgUnitPath": "/CRI/Admin Staff",
            "isMailboxSetup": False,
        }
    )
    return {"status": 201}, content


def list_google_groups(google_groups: List[Dict[str, str]], has_next_page: bool):
    content = {
        "kind": "admin#directory#groups",
        "etag": "etag",
        "groups": [
            {
                "kind": "admin#directory#group",
                "id": google_group.google_id,
                "etag": "",
                "email": google_group.email,
                "name": google_group.people_group.name,
                "directMembersCount": "1",
                "description": "description",
                "adminCreated": True,
                "aliases": [f"{google_group['email'].split('@')[0]}@alias.org"],
                "nonEditableAliases": [
                    f"{google_group['email'].split('@')[0]}@alias.org.test-google-a.com"
                ],
            }
            for google_group in google_groups
        ],
    }
    if has_next_page:
        content["nextPageToken"] = "token"  # nosec
    return {"status": 200}, json.dumps(content)


def add_user_to_group(user: ProjectUser, group: GoogleGroup):
    content = json.dumps(
        {
            "kind": "admin#directory#group",
            "id": user.google_account.google_id,
            "email": user.google_account.email,
            "role": "MEMBER",
            "type": "USER",
            "status": "ACTIVE",
            "delivery_settings": "ALL_MAIL",
        }
    )
    return {"status": 200}, content


def add_user_to_group_already_member():
    content = json.dumps({"error": {"message": "Member already exists"}})
    return {"status": 409}, content
