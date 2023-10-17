import uuid

import factory

from apps.accounts.factories import PeopleGroupFactory, SeedUserFactory
from services.google.models import GoogleAccount, GoogleGroup
from services.google.tasks import create_google_group_task, create_google_user_task


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
        create_google_user_task(self.keycloak_id)
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
        create_google_group_task(self.id)
        self.google_group = google_group
