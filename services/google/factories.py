import uuid

import factory
from django.conf import settings

from apps.accounts.factories import PeopleGroupFactory, SeedUserFactory
from apps.organizations.factories import OrganizationFactory
from services.google.interface import GoogleService
from services.google.models import GoogleAccount, GoogleGroup, GoogleSyncErrors


class RemoteGoogleAccountFactory(SeedUserFactory):
    given_name = factory.LazyAttribute(lambda x: "googlesync")

    @factory.post_generation
    def google_account(self, create, extracted, **kwargs):
        if not create:
            return
        google_account = GoogleAccount.objects.create(
            user=self, organizational_unit="/CRI/Test Google Sync"
        )
        google_account, _ = google_account.create()
        google_account.update_keycloak_username()
        GoogleService.get_user_by_email(google_account.email, 10)
        self.google_account = google_account


class RemoteGoogleGroupFactory(PeopleGroupFactory):
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


class GoogleAccountFactory(factory.django.DjangoModelFactory):
    google_id = factory.Faker("pystr", min_chars=21, max_chars=21)
    email = factory.LazyAttribute(
        lambda x: f"google.account.{uuid.uuid4()}@{settings.GOOGLE_EMAIL_DOMAIN}"
    )
    organizational_unit = "/CRI/Test Google Sync"
    user = factory.LazyAttribute(lambda x: SeedUserFactory(email=x.email))

    class Meta:
        model = GoogleAccount

    @factory.post_generation
    def groups(self, create, extracted, **kwargs):
        if create and extracted:
            self.user.groups.add(*extracted)


class GoogleGroupFactory(factory.django.DjangoModelFactory):
    google_id = factory.Faker("pystr", min_chars=21, max_chars=21)
    email = factory.LazyAttribute(
        lambda x: f"google.group.{uuid.uuid4()}@{settings.GOOGLE_EMAIL_DOMAIN}"
    )
    people_group = factory.SubFactory(
        PeopleGroupFactory, email=email, organization=None
    )

    class Meta:
        model = GoogleGroup

    @factory.post_generation
    def organization(self, create, extracted, **kwargs):
        if create and extracted:
            self.people_group.organization = extracted
            self.people_group.save()
        elif create:
            self.people_group.organization = OrganizationFactory()
            self.people_group.save()


class GoogleSyncErrorFactory(factory.django.DjangoModelFactory):
    error = factory.Faker("text", max_nb_chars=200)

    class Meta:
        model = GoogleSyncErrors
