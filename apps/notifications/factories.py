import factory
from factory.fuzzy import FuzzyChoice

from apps.accounts.factories import UserFactory
from apps.projects.factories import ProjectFactory

from .models import Notification, NotificationSettings


class NotificationFactory(factory.django.DjangoModelFactory):
    sender = factory.SubFactory(UserFactory)
    receiver = factory.SubFactory(UserFactory)
    project = factory.SubFactory(ProjectFactory)
    type = FuzzyChoice(Notification.Types.choices, getter=lambda c: c[0])
    reminder_message = factory.Faker("sentence")
    is_viewed = factory.Faker("boolean")
    to_send = factory.Faker("boolean")

    class Meta:
        model = Notification


class NotificationSettingFactory(factory.django.DjangoModelFactory):
    user = factory.SubFactory(UserFactory)
    notify_added_to_project = factory.Faker("boolean")
    announcement_published = factory.Faker("boolean")
    followed_project_has_been_edited = factory.Faker("boolean")
    project_has_been_commented = factory.Faker("boolean")
    project_has_been_edited = factory.Faker("boolean")
    project_ready_for_review = factory.Faker("boolean")
    project_has_been_reviewed = factory.Faker("boolean")

    class Meta:
        model = NotificationSettings
        django_get_or_create = ("user",)
