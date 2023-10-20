import uuid

import factory

from apps.accounts.factories import PeopleGroupFactory, SeedUserFactory
from services.google.interface import GoogleService
from services.google.models import GoogleAccount, GoogleGroup


class GoogleUserFactory(SeedUserFactory):
    given_name = factory.LazyAttribute(lambda x: "googlesync")

    @factory.post_generation
    def google_account(self, create, extracted, **kwargs):
        if not create:
            return
        google_account = GoogleAccount.objects.create(
            user=self, organizational_unit="/CRI/Test Google Sync"
        )
        google_account = google_account.create()
        google_account.update_keycloak_username()
        GoogleService.get_user_by_email(google_account.email, 10)
        self.google_account = google_account


class GoogleGroupFactory(PeopleGroupFactory):
    name = factory.LazyAttribute(lambda x: f"googlesync-{uuid.uuid4()}")
    email = ""

    @factory.post_generation
    def google_group(self, create, extracted, **kwargs):
        if not create:
            return
        google_group = GoogleGroup.objects.create(people_group=self)
        google_group.create()
        GoogleService.get_group_by_email(google_group.email, 10)
        self.google_group = google_group
