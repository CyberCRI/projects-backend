import factory
from django.utils import timezone

from apps.accounts.factories import PeopleGroupFactory
from apps.commons.factories import language_factory
from apps.organizations.factories import OrganizationFactory

from . import models


class SeedNewsFactory(factory.django.DjangoModelFactory):
    title = factory.Faker("sentence")
    content = factory.Faker("text")
    publication_date = timezone.now()
    created_at = timezone.now()
    updated_at = timezone.now()
    language = language_factory()

    class Meta:
        model = models.News


class NewsFactory(SeedNewsFactory):
    @factory.post_generation
    def organizations(self, create, extracted):
        if not create:
            return
        if extracted:
            for org in extracted:
                self.organizations.add(org)
            if len(extracted) == 0:
                self.organizations.add(OrganizationFactory())
        else:
            self.organizations.add(OrganizationFactory())

    @factory.post_generation
    def people_groups(self, create, extracted):
        if not create:
            return
        if extracted:
            for group in extracted:
                self.people_groups.add(group)
            if len(extracted) == 0:
                self.people_groups.add(PeopleGroupFactory())
        else:
            self.people_groups.add(PeopleGroupFactory())
