import factory

from .interface import KeycloakService
from .models import KeycloakAccount


class KeycloakAccountFactory(factory.django.DjangoModelFactory):
    user = factory.SubFactory("apps.accounts.factories.UserFactory")
    keycloak_id = factory.Faker("uuid4")
    username = factory.Faker("email")
    email = factory.Faker("email")

    class Meta:
        model = KeycloakAccount


class RemoteKeycloakAccountFactory(KeycloakAccountFactory):
    keycloak_id = factory.LazyAttribute(
        lambda x: KeycloakService._create_user(
            {
                "email": x.email,
                "username": x.username,
                "enabled": True,
                "firstName": x.user.given_name,
                "lastName": x.user.family_name,
            }
        )
    )
