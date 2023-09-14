import factory
from django.utils import timezone

from apps.accounts.factories import PeopleGroupFactory, UserFactory
from apps.organizations.factories import OrganizationFactory

from .models import Invitation


class InvitationFactory(factory.django.DjangoModelFactory):
    organization = factory.LazyFunction(
        lambda: OrganizationFactory()
    )  # Subfactory seems to not trigger `create()`
    people_group = factory.SubFactory(PeopleGroupFactory)
    owner = factory.SubFactory(UserFactory)
    expire_at = factory.Faker("date_time", tzinfo=timezone.get_current_timezone())

    class Meta:
        model = Invitation
