import uuid

import factory
from django.utils import timezone
from faker import Faker

from apps.accounts.factories import PeopleGroupFactory, UserFactory
from apps.invitations.models import AccessRequest
from apps.organizations.factories import OrganizationFactory

from .models import Invitation

faker = Faker()


class InvitationFactory(factory.django.DjangoModelFactory):
    organization = factory.LazyFunction(
        lambda: OrganizationFactory()
    )  # Subfactory seems to not trigger `create()`
    people_group = factory.SubFactory(PeopleGroupFactory)
    owner = factory.SubFactory(UserFactory)
    expire_at = factory.Faker("date_time", tzinfo=timezone.get_current_timezone())

    class Meta:
        model = Invitation


class AccessRequestFactory(factory.django.DjangoModelFactory):
    organization = factory.LazyFunction(
        lambda: OrganizationFactory(access_request_enabled=True)
    )  # Subfactory seems to not trigger `create()`
    email = factory.LazyAttribute(
        lambda _: f"request-{uuid.uuid4()}@{faker.domain_name()}".lower()
    )
    given_name = factory.Faker("first_name")
    family_name = factory.Faker("last_name")
    job = factory.Faker("sentence")
    message = factory.Faker("text")

    class Meta:
        model = AccessRequest
