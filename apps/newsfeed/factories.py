import factory
from django.utils import timezone

from apps.accounts.factories import PeopleGroupFactory
from apps.announcements.factories import AnnouncementFactory
from apps.commons.factories import language_factory
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory

from .models import Event, News, Newsfeed


class NewsfeedProjectFactory(factory.django.DjangoModelFactory):
    project = factory.LazyFunction(lambda: ProjectFactory())
    type = Newsfeed.NewsfeedType.PROJECT
    updated_at = factory.Faker("date_time")

    class Meta:
        model = Newsfeed


class NewsfeedAnnouncementFactory(factory.django.DjangoModelFactory):
    announcement = factory.LazyFunction(lambda: AnnouncementFactory())
    type = Newsfeed.NewsfeedType.ANNOUNCEMENT
    updated_at = factory.Faker("date_time")

    class Meta:
        model = Newsfeed


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
            if extracted == "no_people_groups":
                return
            for group in extracted:
                self.people_groups.add(group)
            if len(extracted) == 0:
                self.people_groups.add(
                    PeopleGroupFactory(organization=self.organization)
                )
        else:
            self.people_groups.add(PeopleGroupFactory(organization=self.organization))


class EventFactory(factory.django.DjangoModelFactory):
    organization = factory.LazyFunction(
        lambda: OrganizationFactory()
    )  # Subfactory seems to not trigger `create()`
    title = factory.Faker("sentence")
    content = factory.Faker("text")
    event_date = timezone.now()
    created_at = timezone.now()
    updated_at = timezone.now()

    class Meta:
        model = Event

    @factory.post_generation
    def people_groups(self, create, extracted):
        if not create:
            return
        if extracted:
            if extracted == "no_people_groups":
                return
            for group in extracted:
                self.people_groups.add(group)
            if len(extracted) == 0:
                self.people_groups.add(
                    PeopleGroupFactory(organization=self.organization)
                )
        else:
            self.people_groups.add(PeopleGroupFactory(organization=self.organization))
