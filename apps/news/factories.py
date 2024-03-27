import factory
from django.utils import timezone

from apps.accounts.factories import PeopleGroupFactory
from apps.commons.factories import language_factory
from apps.organizations.factories import OrganizationFactory

from .models import News


class NewsFactory(factory.django.DjangoModelFactory):
    organization = factory.LazyFunction(
        lambda: OrganizationFactory()
    )  # Subfactory seems to not trigger `create()`
    title = factory.Faker("sentence")
    content = factory.Faker("text")
    publication_date = timezone.now()
    created_at = timezone.now()
    updated_at = timezone.now()
    language = language_factory()

    class Meta:
        model = News

    @factory.post_generation
    def people_groups(self, create, extracted):
        if not create:
            return
        if extracted:
            for group in extracted:
                self.people_groups.add(group)
            if len(extracted) == 0:
                self.people_groups.add(
                    PeopleGroupFactory(organization=self.organization)
                )
        else:
            self.people_groups.add(PeopleGroupFactory(organization=self.organization))
