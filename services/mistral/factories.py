import factory
from faker import Faker

from apps.accounts.factories import UserFactory
from apps.projects.factories import ProjectFactory

from .models import ProjectEmbedding, UserEmbedding

faker = Faker()


class ProjectEmbeddingFactory(factory.django.DjangoModelFactory):
    item = factory.LazyFunction(
        lambda: ProjectFactory()
    )  # Subfactory seems to not trigger `create()`
    summary = factory.Faker("text")
    embedding = factory.LazyFunction(
        lambda: [faker.pyfloat(min_value=0, max_value=1) for _ in range(1024)]
    )
    prompt_hashcode = factory.Faker("sha256")
    is_visible = True
    queued_for_update = False

    class Meta:
        model = ProjectEmbedding


class UserEmbeddingFactory(factory.django.DjangoModelFactory):
    item = factory.LazyFunction(lambda: UserFactory())
    embedding = factory.LazyFunction(
        lambda: [faker.pyfloat(min_value=0, max_value=1) for _ in range(1024)]
    )
    prompt_hashcode = factory.Faker("sha256")
    is_visible = True
    queued_for_update = False

    class Meta:
        model = UserEmbedding
