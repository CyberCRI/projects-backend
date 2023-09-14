import factory

from apps.accounts.factories import UserFactory
from apps.projects.factories import ProjectFactory

from .models import Comment, Follow, Review


class CommentFactory(factory.django.DjangoModelFactory):
    project = factory.LazyFunction(
        lambda: ProjectFactory()
    )  # Subfactory seems to not trigger `create()`
    author = factory.SubFactory(UserFactory)
    reply_on = None
    content = factory.Faker("text")

    class Meta:
        model = Comment


class FollowFactory(factory.django.DjangoModelFactory):
    project = factory.LazyFunction(
        lambda: ProjectFactory()
    )  # Subfactory seems to not trigger `create()`
    follower = factory.SubFactory(UserFactory)

    class Meta:
        model = Follow


class ReviewFactory(factory.django.DjangoModelFactory):
    project = factory.LazyFunction(
        lambda: ProjectFactory()
    )  # Subfactory seems to not trigger `create()`
    reviewer = factory.SubFactory(UserFactory)
    description = factory.Faker("text")
    title = factory.Faker("pystr", max_chars=100)

    class Meta:
        model = Review
