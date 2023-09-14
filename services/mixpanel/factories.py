import factory

from apps.projects.factories import ProjectFactory

from .models import MixpanelEvent


class MixpanelEventFactory(factory.django.DjangoModelFactory):
    project = factory.LazyFunction(
        lambda: ProjectFactory()
    )  # Subfactory seems to not trigger `create()`
    mixpanel_id = factory.Faker("pystr", min_chars=36, max_chars=36)
    date = factory.Faker("date")

    class Meta:
        model = MixpanelEvent
