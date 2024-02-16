import factory
from factory.fuzzy import FuzzyChoice

from apps.projects.factories import ProjectFactory
from apps.projects.models import Project

from . import models


class AnnouncementFactory(factory.django.DjangoModelFactory):
    project = factory.LazyFunction(
        lambda: ProjectFactory()
    )  # Subfactory seems to not trigger `create()`
    title = factory.Faker("sentence")
    description = factory.Faker("text")
    type = FuzzyChoice(
        models.Announcement.AnnouncementType.choices, getter=lambda c: c[0]
    )
    status = FuzzyChoice(
        models.Announcement.AnnouncementStatus.choices, getter=lambda c: c[0]
    )
    deadline = None
    is_remunerated = factory.Faker("boolean")

    class Meta:
        model = models.Announcement


class SeedAnnouncementFactory(AnnouncementFactory):
    project = factory.fuzzy.FuzzyChoice(Project.objects.filter())
