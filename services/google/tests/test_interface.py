import time
import uuid
from typing import Callable

from django.conf import settings
from django.urls import reverse

from apps.accounts.factories import PeopleGroupFactory, SeedUserFactory, UserFactory
from apps.accounts.models import PeopleGroup, ProjectUser
from apps.accounts.utils import get_superadmins_group
from apps.commons.test.mixins import skipUnlessGoogle
from apps.commons.test.testcases import JwtAPITestCase
from apps.organizations.factories import OrganizationFactory
from keycloak import KeycloakGetError
from services.google.factories import GoogleGroupFactory, GoogleUserFactory
from services.google.interface import GoogleService
from services.google.models import GoogleAccount, GoogleGroup
from services.keycloak.interface import KeycloakService


@skipUnlessGoogle
class GoogleServiceTestCase(JwtAPITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        superadmin_group = get_superadmins_group()
        cls.user = UserFactory(groups=[superadmin_group])
        cls.organization = OrganizationFactory(code="TEST_GOOGLE_SYNC")

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=self.user)

    def tearDown(self):
        for google_account in GoogleAccount.objects.filter(
            user__given_name="googlesync"
        ):
            user = google_account.user
            GoogleService.delete_user(google_account)
            try:
                KeycloakService.get_user(user.keycloak_id)
                KeycloakService.delete_user(user)
            except KeycloakGetError:
                pass
        for google_group in GoogleGroup.objects.filter(
            people_group__name__startswith="googlesync"
        ):
            GoogleService.delete_group(google_group)
        return super().tearDown()
    
    def retry_test_assertion(self, func: Callable, retries: int = 30, delay: int = 2):
        for _ in range(retries):
            try:
                func()
                return
            except AssertionError:
                time.sleep(delay)
        func()

    def test_get_user(self):
        pass
    
    def test_get_user_by_email(self):
        pass

    def test_get_user_by_id(self):
        pass

    def test_create_user(self):
        pass
    
    def test_update_user(self):
        pass

    def test_suspend_user(self):
        user = GoogleUserFactory(groups=[self.organization.get_users()])
        GoogleService.suspend_user(user.google_account)
        def test_result():
            google_user = GoogleService.get_user_by_email(user.email, 5)
            assert google_user["suspended"] is True
        self.retry_test_assertion(test_result)
    
    def test_delete_user(self):
        user = GoogleUserFactory(groups=[self.organization.get_users()])
        GoogleService.delete_user(user.google_account)
        def test_result():
            google_user = GoogleService.get_user_by_email(user.email, 5)
            assert google_user is None
        self.retry_test_assertion(test_result)
    
    def test_add_user_alias(self):
        user = GoogleUserFactory(groups=[self.organization.get_users()])
        GoogleService.add_user_alias(user.google_account)
        alias = user.email.replace(
            settings.GOOGLE_EMAIL_DOMAIN, settings.GOOGLE_EMAIL_ALIAS_DOMAIN
        )
        def test_result():    
            google_user = GoogleService.get_user_by_email(user.email, 5)
            emails = [email["address"] for email in google_user["emails"]]
            assert alias in emails
        self.retry_test_assertion(test_result)
    
    def test_get_user_groups(self):
        pass
    
    def test_get_group_by_email(self):
        pass

    def test_get_group_by_id(self):
        pass

    def test_get_groups(self):
        pass

    def test_create_group(self):
        pass

    def test_add_group_alias(self):
        pass

    def test_update_group(self):
        pass

    def test_delete_group(self):
        pass

    def test_get_group_members(self):
        pass

    def test_add_user_to_group(self):
        pass

    def test_remove_user_from_group(self):
        pass

    def test_get_org_units(self):
        pass
