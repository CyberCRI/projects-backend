import factory
from django.utils import timezone

from apps.announcements.factories import AnnouncementFactory
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory

from .models import Event, Instruction, News, Newsfeed


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
    visible_by_all = False

    class Meta:
        model = News

    @factory.post_generation
    def people_groups(self, create, extracted, **kwargs):
        if create and extracted:
            self.people_groups.add(*extracted)


class InstructionFactory(factory.django.DjangoModelFactory):
    organization = factory.LazyFunction(
        lambda: OrganizationFactory()
    )  # Subfactory seems to not trigger `create()`
    title = factory.Faker("sentence")
    content = factory.Faker("text")
    publication_date = timezone.now()
    visible_by_all = False

    class Meta:
        model = Instruction

    @factory.post_generation
    def people_groups(self, create, extracted, **kwargs):
        if create and extracted:
            self.people_groups.add(*extracted)


class EventFactory(factory.django.DjangoModelFactory):
    organization = factory.LazyFunction(
        lambda: OrganizationFactory()
    )  # Subfactory seems to not trigger `create()`
    title = factory.Faker("sentence")
    content = factory.Faker("text")
    event_date = timezone.now()
    visible_by_all = False

    class Meta:
        model = Event

    @factory.post_generation
    def people_groups(self, create, extracted, **kwargs):
        if create and extracted:
            self.people_groups.add(*extracted)
