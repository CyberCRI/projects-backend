import factory
from factory.fuzzy import FuzzyChoice

from apps.projects.factories import ProjectFactory

from .models import Goal


class GoalFactory(factory.django.DjangoModelFactory):
    project = factory.LazyFunction(
        lambda: ProjectFactory()
    )  # Subfactory seems to not trigger `create()`
    title = factory.Faker("text", max_nb_chars=255)
    description = factory.Faker("text")
    deadline_at = factory.Faker("date_time")
    status = FuzzyChoice(Goal.GoalStatus.choices, getter=lambda c: c[0])

    class Meta:
        model = Goal
