import factory
from faker import Faker

from apps.accounts.factories import UserFactory
from apps.projects.factories import ProjectFactory

from .models import (
    ProjectEmbedding,
    UserEmbedding,
    UserProfileEmbedding,
    UserProjectsEmbedding,
)

faker = Faker()


class ProjectEmbeddingFactory(factory.django.DjangoModelFactory):
    item = factory.LazyFunction(
        lambda: ProjectFactory()
    )  # Subfactory seems to not trigger `create()`

    class Meta:
        model = ProjectEmbedding


class UserProfileEmbeddingFactory(factory.django.DjangoModelFactory):
    item = factory.LazyFunction(lambda: UserFactory())

    class Meta:
        model = UserProfileEmbedding


class UserProjectsEmbeddingFactory(factory.django.DjangoModelFactory):
    item = factory.LazyFunction(lambda: UserFactory())

    class Meta:
        model = UserProjectsEmbedding


class UserEmbeddingFactory(factory.django.DjangoModelFactory):
    item = factory.LazyFunction(lambda: UserFactory())

    class Meta:
        model = UserEmbedding
