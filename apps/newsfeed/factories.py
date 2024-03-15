import factory

from apps.announcements.factories import AnnouncementFactory
from apps.projects.factories import ProjectFactory

from . import models


class NewsfeedProjectFactory(factory.django.DjangoModelFactory):
    project = factory.LazyFunction(lambda: ProjectFactory())
    type = models.Newsfeed.NewsfeedType.PROJECT
    updated_at = factory.Faker("date_time")

    class Meta:
        model = models.Newsfeed


class NewsfeedAnnouncementFactory(factory.django.DjangoModelFactory):
    announcement = factory.LazyFunction(lambda: AnnouncementFactory())
    type = models.Newsfeed.NewsfeedType.ANNOUNCEMENT
    updated_at = factory.Faker("date_time")

    class Meta:
        model = models.Newsfeed
