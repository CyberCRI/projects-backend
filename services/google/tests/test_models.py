import time
import uuid
from unittest.mock import patch

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
from services.google.models import GoogleAccount
from services.google.tasks import (
    create_google_group_task,
    create_google_user_task,
    suspend_google_user_task,
    update_google_group_task,
    update_google_user_task,
)
from services.keycloak.interface import KeycloakService


class GoogleAccountTestCase(JwtAPITestCase):
    def tearDown(self):
        for user in ProjectUser.objects.filter(google_account__isnull=False):
            GoogleService.delete_user(user.google_account)
            try:
                KeycloakService.get_user(user.keycloak_id)
                KeycloakService.delete_user(user)
            except KeycloakGetError:
                pass
        for group in PeopleGroup.objects.filter(google_group__isnull=False):
            GoogleService.delete_group(group.google_group)
        return super().tearDown()
    
    def test_create_user(self):
        user = SeedUserFactory()
        google_account = GoogleAccount.objects.create(user=user)
        google_account.create()