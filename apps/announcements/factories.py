import factory
from factory.fuzzy import FuzzyChoice

from apps.projects.factories import ProjectFactory

from .models import Announcement


class AnnouncementFactory(factory.django.DjangoModelFactory):
    project = factory.LazyFunction(
        lambda: ProjectFactory()
    )  # Subfactory seems to not trigger `create()`
    title = factory.Faker("sentence")
    description = factory.Faker("text")
    type = FuzzyChoice(Announcement.AnnouncementType.choices, getter=lambda c: c[0])
    status = FuzzyChoice(Announcement.AnnouncementStatus.choices, getter=lambda c: c[0])
    deadline = None
    is_remunerated = factory.Faker("boolean")

    class Meta:
        model = Announcement
