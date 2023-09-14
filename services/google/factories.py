import uuid

import factory
from django.conf import settings

from apps.accounts.factories import PeopleGroupFactory, SeedUserFactory
from services.google.interface import GoogleService
from services.keycloak.interface import KeycloakService


class GoogleUserFactory(SeedUserFactory):
    given_name = factory.LazyAttribute(lambda x: "googlesync")
    email = factory.LazyAttribute(
        lambda _: f"{uuid.uuid4()}@{settings.GOOGLE_EMAIL_DOMAIN}"
    )

    @classmethod
    def create(cls, **kwargs):
        user = super().create(**kwargs)
        google_user = GoogleService.create_user(user, "Test Google Sync")
        user.personal_email = user.email
        user.email = google_user["primaryEmail"]
        user.save()
        GoogleService.get_user(user.email, 5)
        KeycloakService.update_user(user)
        return user


class GoogleGroupFactory(PeopleGroupFactory):
    name = factory.LazyAttribute(lambda x: f"googlesync-{uuid.uuid4()}")
    email = ""

    @classmethod
    def create(cls, **kwargs):
        group = super().create(**kwargs)
        google_group = GoogleService.create_group(group)
        group.email = google_group["email"]
        group.save()
        GoogleService.get_group(group.email, 5)
        return group
