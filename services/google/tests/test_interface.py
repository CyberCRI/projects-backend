import time
import uuid
from typing import Callable

from django.conf import settings
from keycloak import KeycloakGetError

from apps.accounts.factories import PeopleGroupFactory, UserFactory
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase, skipUnlessGoogle
from apps.organizations.factories import OrganizationFactory
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
            self.assertIsNotNone(google_user)
            self.assertEqual(google_user["id"], user.google_account.google_id)

        self.retry_test_assertion(test_result)

    def test_get_user_by_email(self):
        user = RemoteGoogleAccountFactory(groups=[self.organization.get_users()])

        def test_result():
            google_user = GoogleService.get_user_by_email(user.email)
            self.assertIsNotNone(google_user)
            self.assertEqual(google_user["id"], user.google_account.google_id)

        self.retry_test_assertion(test_result)

    def test_create_user(self):
        user = UserFactory(groups=[self.organization.get_users()])
        response = GoogleService.create_user(
            user, organizational_unit="/CRI/Test Google Sync"
        )

        def test_result():
            google_user = GoogleService.get_user_by_id(response["id"])
            self.assertIsNotNone(google_user)
            self.assertIsNotNone(google_user["id"])
            self.assertEqual(google_user["orgUnitPath"], "/CRI/Test Google Sync")
            self.assertTrue(
                google_user["primaryEmail"].startswith(
                    f"test.{user.given_name}.{user.family_name}".lower()
                )
            )
            self.assertEqual(google_user["name"]["givenName"], user.given_name)
            self.assertEqual(google_user["name"]["familyName"], user.family_name)

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
            self.assertIsNotNone(google_user)
            self.assertEqual(google_user["name"]["familyName"], "test update")
            self.assertEqual(google_user["orgUnitPath"], "/CRI/Test Google Sync Update")

        self.retry_test_assertion(test_result)

    def test_suspend_user(self):
        user = RemoteGoogleAccountFactory(groups=[self.organization.get_users()])
        GoogleService.suspend_user(user.google_account)

        def test_result():
            google_user = GoogleService.get_user_by_email(user.email)
            self.assertIsNotNone(google_user)
            self.assertTrue(google_user["suspended"])

        self.retry_test_assertion(test_result)

    def test_delete_user(self):
        user = RemoteGoogleAccountFactory(groups=[self.organization.get_users()])
        GoogleService.delete_user(user.google_account)

        def test_result():
            google_user = GoogleService.get_user_by_email(user.email, 5)
            self.assertIsNone(google_user)

        self.retry_test_assertion(test_result)

    def test_add_user_alias(self):
        user = RemoteGoogleAccountFactory(groups=[self.organization.get_users()])
        GoogleService.add_user_alias(user.google_account)
        alias = user.email.replace(
            settings.GOOGLE_EMAIL_DOMAIN, settings.GOOGLE_EMAIL_ALIAS_DOMAIN
        )

        def test_result():
            google_user = GoogleService.get_user_by_email(user.email)
            self.assertIsNotNone(google_user)
            emails = [email["address"] for email in google_user["emails"]]
            self.assertIn(alias, emails)

        self.retry_test_assertion(test_result)

    def test_get_user_groups(self):
        user = RemoteGoogleAccountFactory(groups=[self.organization.get_users()])
        group_1 = RemoteGoogleGroupFactory(organization=self.organization)
        group_2 = RemoteGoogleGroupFactory(organization=self.organization)
        GoogleService.add_user_to_group(user.google_account, group_1.google_group)
        GoogleService.add_user_to_group(user.google_account, group_2.google_group)

        def test_result():
            google_groups = GoogleService.get_user_groups(user.google_account)
            self.assertIsNotNone(google_groups)
            self.assertIn(
                group_1.google_group.google_id, [group["id"] for group in google_groups]
            )
            self.assertIn(
                group_2.google_group.google_id, [group["id"] for group in google_groups]
            )

        self.retry_test_assertion(test_result)

    def test_get_group_by_email(self):
        group = RemoteGoogleGroupFactory(organization=self.organization)

        def test_result():
            google_group = GoogleService.get_group_by_email(group.email)
            self.assertIsNotNone(google_group)
            self.assertEqual(google_group["id"], group.google_group.google_id)

        self.retry_test_assertion(test_result)

    def test_get_group_by_id(self):
        group = RemoteGoogleGroupFactory(organization=self.organization)

        def test_result():
            google_group = GoogleService.get_group_by_id(group.google_group.google_id)
            self.assertIsNotNone(google_group)
            self.assertEqual(google_group["id"], group.google_group.google_id)

        self.retry_test_assertion(test_result)

    def test_get_groups(self):
        group_1 = RemoteGoogleGroupFactory(organization=self.organization)
        group_2 = RemoteGoogleGroupFactory(organization=self.organization)

        def test_result():
            google_groups = GoogleService.get_groups()
            self.assertNotEqual(google_groups, [])
            self.assertGreater(len(google_groups), 0)
            self.assertIn(
                group_1.google_group.google_id, [group["id"] for group in google_groups]
            )
            self.assertIn(
                group_2.google_group.google_id, [group["id"] for group in google_groups]
            )

        self.retry_test_assertion(test_result)

    def test_create_group(self):
        group = PeopleGroupFactory(
            organization=self.organization, email="", name=f"googlesync-{uuid.uuid4()}"
        )
        response = GoogleService.create_group(group)

        def test_result():
            google_group = GoogleService.get_group_by_id(response["id"])
            self.assertIsNotNone(google_group)
            self.assertIsNotNone(google_group["id"])
            self.assertTrue(
                google_group["email"].startswith(
                    f"test.team.{group.name}".replace("-", "")
                )
            )
            self.assertEqual(google_group["name"], group.name)

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
            self.assertIsNotNone(google_group)
            self.assertIsNotNone(google_group["id"])
            self.assertEqual(google_group["email"], group.email)
            self.assertEqual(google_group["name"], group.name)

        self.retry_test_assertion(test_result)

    def test_add_group_alias(self):
        group = RemoteGoogleGroupFactory(organization=self.organization)
        GoogleService.add_group_alias(group.google_group)
        alias = group.email.replace(
            settings.GOOGLE_EMAIL_DOMAIN, settings.GOOGLE_EMAIL_ALIAS_DOMAIN
        )

        def test_result():
            google_group = GoogleService.get_group_by_email(group.email)
            self.assertIsNotNone(google_group)
            self.assertIn("aliases", google_group)
            self.assertIn(alias, google_group["aliases"])

        self.retry_test_assertion(test_result)

    def test_update_group(self):
        group = RemoteGoogleGroupFactory(organization=self.organization)
        group.name = "test update"
        group.save()
        GoogleService.update_group(group.google_group)

        def test_result():
            google_group = GoogleService.get_group_by_email(group.email)
            self.assertIsNotNone(google_group)
            self.assertEqual(google_group["name"], "test update")

        self.retry_test_assertion(test_result)

    def test_delete_group(self):
        group = RemoteGoogleGroupFactory(organization=self.organization)
        GoogleService.delete_group(group.google_group)

        def test_result():
            google_group = GoogleService.get_group_by_email(group.email, 5)
            self.assertIsNone(google_group)

        self.retry_test_assertion(test_result)

    def test_get_group_members(self):
        group = RemoteGoogleGroupFactory(organization=self.organization)
        user_1 = RemoteGoogleAccountFactory(groups=[self.organization.get_users()])
        user_2 = RemoteGoogleAccountFactory(groups=[self.organization.get_users()])
        GoogleService.add_user_to_group(user_1.google_account, group.google_group)
        GoogleService.add_user_to_group(user_2.google_account, group.google_group)

        def test_result():
            google_members = GoogleService.get_group_members(group.google_group)
            self.assertIsNotNone(google_members)
            self.assertIn(
                user_1.google_account.google_id,
                [member["id"] for member in google_members],
            )
            self.assertIn(
                user_2.google_account.google_id,
                [member["id"] for member in google_members],
            )

        self.retry_test_assertion(test_result)

    def test_add_and_remove_user_to_group(self):
        group = RemoteGoogleGroupFactory(organization=self.organization)
        user = RemoteGoogleAccountFactory(groups=[self.organization.get_users()])
        GoogleService.add_user_to_group(user.google_account, group.google_group)

        def test_add_result():
            google_members = GoogleService.get_group_members(group.google_group)
            self.assertIsNotNone(google_members)
            self.assertIn(
                user.google_account.google_id,
                [member["id"] for member in google_members],
            )

        self.retry_test_assertion(test_add_result)
        GoogleService.remove_user_from_group(user.google_account, group.google_group)

        def test_remove_result():
            google_members = GoogleService.get_group_members(group.google_group)
            self.assertIsNotNone(google_members)
            self.assertNotIn(
                user.google_account.google_id,
                [member["id"] for member in google_members],
            )

        self.retry_test_assertion(test_remove_result)

    def test_get_org_units(self):
        org_units = GoogleService.get_org_units()
        self.assertSetEqual(
            set(org_units),
            {
                "/CRI",
                "/CRI/Test Google Sync",
                "/CRI/Test Google Sync Update",
                "/CRI/Admin Staff",
            },
        )
