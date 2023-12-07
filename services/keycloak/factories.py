import factory

from .interface import KeycloakService
from .models import KeycloakAccount


class KeycloakAccountFactory(factory.django.DjangoModelFactory):
    user = factory.SubFactory("apps.accounts.factories.UserFactory")
    keycloak_id = factory.Faker("uuid4")
    username = factory.Faker("email")
    email = factory.Faker("email")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")

    class Meta:
        model = KeycloakAccount


class RemoteKeycloakAccountFactory(KeycloakAccountFactory):
    keycloak_id = factory.LazyAttribute(
        lambda x: KeycloakService._create_user(
            {
                "email": x.email,
                "username": x.username,
                "enabled": True,
                "firstName": x.first_name,
                "lastName": x.last_name,
            }
        )
    )
