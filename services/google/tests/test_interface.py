import time
import uuid
from typing import Callable

from django.conf import settings

from apps.accounts.factories import PeopleGroupFactory, UserFactory
from apps.accounts.utils import get_superadmins_group
from apps.commons.test.mixins import skipUnlessGoogle
from apps.commons.test.testcases import JwtAPITestCase
from apps.organizations.factories import OrganizationFactory
from keycloak import KeycloakGetError
from services.google.factories import (
    RemoteGoogleAccountFactory,
    RemoteGoogleGroupFactory,
)
from services.google.interface import GoogleService
from services.google.models import GoogleAccount, GoogleGroup
from services.keycloak.interface import KeycloakService


@skipUnlessGoogle
class GoogleServiceTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        superadmin_group = get_superadmins_group()
        cls.user = UserFactory(groups=[superadmin_group])
        cls.organization = OrganizationFactory(code="TEST_GOOGLE_SYNC")

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=self.user)

    @classmethod
    def tearDownClass(cls):
        for google_account in GoogleAccount.objects.filter(
            user__given_name="googlesync"
        ):
            user = google_account.user
            GoogleService.delete_user(google_account)
            try:
                KeycloakService.get_user(user.keycloak_id)
                KeycloakService.delete_user(user.keycloak_account)
            except KeycloakGetError:
                pass
        for google_group in GoogleGroup.objects.filter(
            people_group__name__startswith="googlesync"
        ):
            GoogleService.delete_group(google_group)
        return super().tearDownClass()

    def retry_test_assertion(self, func: Callable, retries: int = 30, delay: int = 2):
        for _ in range(retries):
            try:
                func()
                return
            except AssertionError:
                time.sleep(delay)
        func()

    def test_get_user_by_id(self):
        user = RemoteGoogleAccountFactory(groups=[self.organization.get_users()])

        def test_result():
            google_user = GoogleService.get_user_by_id(user.google_account.google_id)
            assert google_user is not None
            assert google_user["id"] == user.google_account.google_id

        self.retry_test_assertion(test_result)

    def test_get_user_by_email(self):
        user = RemoteGoogleAccountFactory(groups=[self.organization.get_users()])

        def test_result():
            google_user = GoogleService.get_user_by_email(user.email)
            assert google_user is not None
            assert google_user["id"] == user.google_account.google_id

        self.retry_test_assertion(test_result)

    def test_create_user(self):
        user = UserFactory(groups=[self.organization.get_users()])
        response = GoogleService.create_user(
            user, organizational_unit="/CRI/Test Google Sync"
        )

        def test_result():
            google_user = GoogleService.get_user_by_id(response["id"])
            assert google_user is not None
            assert google_user["id"] is not None
            assert google_user["orgUnitPath"] == "/CRI/Test Google Sync"
            assert google_user["primaryEmail"].startswith(
                f"test.{user.given_name}.{user.family_name}".lower()
            )
            assert google_user["name"]["givenName"] == user.given_name
            assert google_user["name"]["familyName"] == user.family_name

        self.retry_test_assertion(test_result)
        GoogleService.service().users().delete(userKey=response["id"]).execute()

    def test_update_user(self):
        user = RemoteGoogleAccountFactory(
            family_name="test", groups=[self.organization.get_users()]
        )
        user.google_account.organizational_unit = "/CRI/Test Google Sync Update"
        user.google_account.save()
        user.family_name = "test update"
        GoogleService.update_user(user.google_account)

        def test_result():
            google_user = GoogleService.get_user_by_email(user.google_account.email)
            assert google_user is not None
            assert google_user["name"]["familyName"] == "test update"
            assert google_user["orgUnitPath"] == "/CRI/Test Google Sync Update"

        self.retry_test_assertion(test_result)

    def test_suspend_user(self):
        user = RemoteGoogleAccountFactory(groups=[self.organization.get_users()])
        GoogleService.suspend_user(user.google_account)

        def test_result():
            google_user = GoogleService.get_user_by_email(user.email)
            assert google_user is not None
            assert google_user["suspended"] is True

        self.retry_test_assertion(test_result)

    def test_delete_user(self):
        user = RemoteGoogleAccountFactory(groups=[self.organization.get_users()])
        GoogleService.delete_user(user.google_account)

        def test_result():
            google_user = GoogleService.get_user_by_email(user.email, 5)
            assert google_user is None

        self.retry_test_assertion(test_result)

    def test_add_user_alias(self):
        user = RemoteGoogleAccountFactory(groups=[self.organization.get_users()])
        GoogleService.add_user_alias(user.google_account)
        alias = user.email.replace(
            settings.GOOGLE_EMAIL_DOMAIN, settings.GOOGLE_EMAIL_ALIAS_DOMAIN
        )

        def test_result():
            google_user = GoogleService.get_user_by_email(user.email)
            assert google_user is not None
            emails = [email["address"] for email in google_user["emails"]]
            assert alias in emails

        self.retry_test_assertion(test_result)

    def test_get_user_groups(self):
        user = RemoteGoogleAccountFactory(groups=[self.organization.get_users()])
        group_1 = RemoteGoogleGroupFactory(organization=self.organization)
        group_2 = RemoteGoogleGroupFactory(organization=self.organization)
        GoogleService.add_user_to_group(user.google_account, group_1.google_group)
        GoogleService.add_user_to_group(user.google_account, group_2.google_group)

        def test_result():
            google_groups = GoogleService.get_user_groups(user.google_account)
            assert google_groups is not None
            assert {
                group_1.google_group.google_id,
                group_2.google_group.google_id,
            }.issubset({group["id"] for group in google_groups})

        self.retry_test_assertion(test_result)

    def test_get_group_by_email(self):
        group = RemoteGoogleGroupFactory(organization=self.organization)

        def test_result():
            google_group = GoogleService.get_group_by_email(group.email)
            assert google_group is not None
            assert google_group["id"] == group.google_group.google_id

        self.retry_test_assertion(test_result)

    def test_get_group_by_id(self):
        group = RemoteGoogleGroupFactory(organization=self.organization)

        def test_result():
            google_group = GoogleService.get_group_by_id(group.google_group.google_id)
            assert google_group is not None
            assert google_group["id"] == group.google_group.google_id

        self.retry_test_assertion(test_result)

    def test_get_groups(self):
        group_1 = RemoteGoogleGroupFactory(organization=self.organization)
        group_2 = RemoteGoogleGroupFactory(organization=self.organization)

        def test_result():
            google_groups = GoogleService.get_groups()
            assert google_groups != []
            assert len(google_groups) > 0
            assert {
                group_1.google_group.google_id,
                group_2.google_group.google_id,
            }.issubset({group["id"] for group in google_groups})

        self.retry_test_assertion(test_result)

    def test_create_group(self):
        group = PeopleGroupFactory(
            organization=self.organization, email="", name=f"googlesync-{uuid.uuid4()}"
        )
        response = GoogleService.create_group(group)

        def test_result():
            google_group = GoogleService.get_group_by_id(response["id"])
            assert google_group is not None
            assert google_group["id"] is not None
            assert google_group["email"].startswith(
                f"test.team.{group.name}".replace("-", "")
            )
            assert google_group["name"] == group.name

        self.retry_test_assertion(test_result)
        GoogleService.service().groups().delete(groupKey=response["id"]).execute()

    def test_create_group_with_email(self):
        group = PeopleGroupFactory(
            organization=self.organization,
            email=f"test.team.googlesync.{uuid.uuid4()}@{settings.GOOGLE_EMAIL_DOMAIN}",
        )
        response = GoogleService.create_group(group)

        def test_result():
            google_group = GoogleService.get_group_by_id(response["id"])
            assert google_group is not None
            assert google_group["id"] is not None
            assert google_group["email"] == group.email
            assert google_group["name"] == group.name

        self.retry_test_assertion(test_result)

    def test_add_group_alias(self):
        group = RemoteGoogleGroupFactory(organization=self.organization)
        GoogleService.add_group_alias(group.google_group)
        alias = group.email.replace(
            settings.GOOGLE_EMAIL_DOMAIN, settings.GOOGLE_EMAIL_ALIAS_DOMAIN
        )

        def test_result():
            google_group = GoogleService.get_group_by_email(group.email)
            assert google_group is not None
            assert "aliases" in google_group
            assert alias in google_group["aliases"]

        self.retry_test_assertion(test_result)

    def test_update_group(self):
        group = RemoteGoogleGroupFactory(organization=self.organization)
        group.name = "test update"
        group.save()
        GoogleService.update_group(group.google_group)

        def test_result():
            google_group = GoogleService.get_group_by_email(group.email)
            assert google_group is not None
            assert google_group["name"] == "test update"

        self.retry_test_assertion(test_result)

    def test_delete_group(self):
        group = RemoteGoogleGroupFactory(organization=self.organization)
        GoogleService.delete_group(group.google_group)

        def test_result():
            google_group = GoogleService.get_group_by_email(group.email, 5)
            assert google_group is None

        self.retry_test_assertion(test_result)

    def test_get_group_members(self):
        group = RemoteGoogleGroupFactory(organization=self.organization)
        user_1 = RemoteGoogleAccountFactory(groups=[self.organization.get_users()])
        user_2 = RemoteGoogleAccountFactory(groups=[self.organization.get_users()])
        GoogleService.add_user_to_group(user_1.google_account, group.google_group)
        GoogleService.add_user_to_group(user_2.google_account, group.google_group)

        def test_result():
            google_members = GoogleService.get_group_members(group.google_group)
            assert google_members is not None
            assert {
                user_1.google_account.google_id,
                user_2.google_account.google_id,
            }.issubset({member["id"] for member in google_members})

        self.retry_test_assertion(test_result)

    def test_add_and_remove_user_to_group(self):
        group = RemoteGoogleGroupFactory(organization=self.organization)
        user = RemoteGoogleAccountFactory(groups=[self.organization.get_users()])
        GoogleService.add_user_to_group(user.google_account, group.google_group)

        def test_add_result():
            google_members = GoogleService.get_group_members(group.google_group)
            assert google_members is not None
            assert user.google_account.google_id in {
                member["id"] for member in google_members
            }

        self.retry_test_assertion(test_add_result)
        GoogleService.remove_user_from_group(user.google_account, group.google_group)

        def test_remove_result():
            google_members = GoogleService.get_group_members(group.google_group)
            assert google_members is not None
            assert user.google_account.google_id not in {
                member["id"] for member in google_members
            }

        self.retry_test_assertion(test_remove_result)

    def test_get_org_units(self):
        org_units = GoogleService.get_org_units()
        assert set(org_units) == {
            "/CRI",
            "/CRI/Test Google Sync",
            "/CRI/Test Google Sync Update",
            "/CRI/Admin Staff",
        }
