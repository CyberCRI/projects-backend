import factory

from .models import KeycloakAccount


class KeycloakAccountFactory(factory.django.DjangoModelFactory):
    user = factory.SubFactory("apps.accounts.factories.UserFactory")
    keycloak_id = factory.Faker("uuid4")
    username = factory.Faker("email")
    email = factory.Faker("email")

    class Meta:
        model = KeycloakAccount
