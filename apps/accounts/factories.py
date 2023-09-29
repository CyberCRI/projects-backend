import uuid

import factory
from factory.fuzzy import FuzzyInteger
from faker import Faker
from guardian.shortcuts import assign_perm

from apps.accounts.utils import get_default_group
from apps.commons.factories import sdg_factory
from services.keycloak.interface import KeycloakService

from .models import PeopleGroup, PrivacySettings, ProjectUser, Skill

faker = Faker()


class UserFactory(factory.django.DjangoModelFactory):
    keycloak_id = factory.Faker("uuid4")
    people_id = factory.Faker("uuid4")
    email = factory.Faker("email")
    given_name = factory.Faker("first_name")
    family_name = factory.Faker("last_name")

    birthdate = factory.Faker("date_of_birth", minimum_age=1)
    pronouns = factory.Faker("pystr", min_chars=8, max_chars=8)
    personal_description = factory.Faker("text")
    short_description = factory.Faker("text")
    professional_description = factory.Faker("text")
    location = factory.Faker("sentence")
    job = factory.Faker("sentence")
    sdgs = factory.List([sdg_factory() for _ in range(FuzzyInteger(0, 17).fuzz())])

    facebook = factory.Faker("url")
    mobile_phone = factory.Faker("pystr", min_chars=8, max_chars=8)
    linkedin = factory.Faker("url")
    medium = factory.Faker("url")
    website = factory.Faker("pystr", min_chars=8, max_chars=8)
    personal_email = factory.Faker("email")
    skype = factory.Faker("pystr", min_chars=8, max_chars=8)
    landline_phone = factory.Faker("pystr", min_chars=8, max_chars=8)
    twitter = factory.Faker("url")

    class Meta:
        model = ProjectUser
        django_get_or_create = ("email", "keycloak_id")

    # https://factoryboy.readthedocs.io/en/stable/recipes.html#simple-many-to-many-relationship
    @factory.post_generation
    def groups(self, create, extracted, **kwargs):
        if not create:
            return
        self.groups.add(*[get_default_group(), *(extracted if extracted else [])])

    @factory.post_generation
    def permissions(self, create, extracted, **kwargs):
        if extracted:
            for permission, obj in extracted:
                if obj is None:
                    assign_perm(permission, self)
                else:
                    assign_perm(permission, self, obj)

    @factory.post_generation
    def publication_status(self, create, extracted, **kwargs):
        if not create:
            return
        publication_status = (
            extracted if extracted else PrivacySettings.PrivacyChoices.PUBLIC
        )
        self.privacy_settings.publication_status = publication_status
        self.privacy_settings.save()


class SeedUserFactory(UserFactory):
    email = factory.LazyAttribute(lambda x: f"{uuid.uuid4()}@example.org")

    @factory.lazy_attribute
    def keycloak_id(self):
        keycloak_data = {
            "email": self.email,
            "username": self.email,
            "enabled": True,
            "firstName": self.given_name,
            "lastName": self.family_name,
            "attributes": {
                "pid": [self.people_id],
            },
            "credentials": [
                {
                    "value": "password",
                    "type": "password",
                }
            ],
        }
        return KeycloakService._create_user(keycloak_data)


class KeycloakAccountFactory:
    def __init__(self, groups=None):
        self.pid = faker.uuid4()
        self.username = f"{uuid.uuid4()}@example.org"
        self.email = f"{uuid.uuid4()}@example.org"
        self.first_name = faker.first_name()
        self.last_name = faker.last_name()

        keycloak_data = {
            "email": self.email,
            "username": self.username,
            "enabled": True,
            "firstName": self.first_name,
            "lastName": self.last_name,
            "attributes": {
                "pid": [self.pid],
            },
        }
        self.keycloak_id = KeycloakService._create_user(keycloak_data)
        groups = groups if groups else []
        for group in groups:
            KeycloakService.add_user_to_keycloak_group(self.keycloak_id, group)


class PeopleGroupFactory(factory.django.DjangoModelFactory):
    organization = factory.SubFactory(
        "apps.organizations.factories.OrganizationFactory"
    )
    description = factory.Faker("text")
    email = factory.Faker("email")
    name = factory.Faker("name")
    publication_status = PeopleGroup.PublicationStatus.ORG

    class Meta:
        model = PeopleGroup

    @classmethod
    def create(cls, **kwargs):
        instance = super().create(**kwargs)
        instance.setup_permissions()
        return instance


class SkillFactory(factory.django.DjangoModelFactory):
    user = factory.SubFactory(UserFactory)
    wikipedia_tag = factory.SubFactory("apps.misc.factories.WikipediaTagFactory")
    level = factory.Faker("random_digit")
    level_to_reach = factory.Faker("random_digit")

    class Meta:
        model = Skill
