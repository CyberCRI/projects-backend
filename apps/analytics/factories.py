import factory
from django.utils import timezone

from apps.projects.factories import ProjectFactory

from .models import Stat


class StatFactory(factory.django.DjangoModelFactory):
    project = factory.SubFactory(ProjectFactory)
    comments = 0
    replies = 0
    follows = 0
    links = 0
    files = 0
    blog_entries = 0
    goals = 0
    versions = 0
    description_length = 0
    last_update = factory.LazyFunction(timezone.now)

    class Meta:
        model = Stat
