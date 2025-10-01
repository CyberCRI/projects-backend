import factory
from faker import Faker

from apps.accounts.factories import UserFactory
from apps.projects.factories import ProjectFactory
from apps.skills.factories import TagFactory

from .models import (
    ProjectEmbedding,
    TagEmbedding,
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


class TagEmbeddingFactory(factory.django.DjangoModelFactory):
    item = factory.LazyFunction(lambda: TagFactory())

    class Meta:
        model = TagEmbedding
