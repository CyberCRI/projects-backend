import uuid

import factory
from factory.fuzzy import FuzzyInteger
from faker import Faker

from apps.accounts.utils import get_default_group
from apps.commons.factories import sdg_factory
from services.keycloak.factories import KeycloakAccountFactory
from services.keycloak.interface import KeycloakService

from .models import PeopleGroup, PrivacySettings, ProjectUser, UserScore

faker = Faker()


class UserFactory(factory.django.DjangoModelFactory):
    people_id = factory.Faker("uuid4")
    email = factory.Sequence(lambda n: f"{n}.{faker.email()}")
    given_name = factory.Faker("first_name")
    family_name = factory.Faker("last_name")

    birthdate = factory.Faker("date_of_birth", minimum_age=1)
    pronouns = factory.Faker("prefix")
    description = factory.Faker("text")
    short_description = factory.Faker("text")
    location = factory.Faker("city")
    job = factory.Faker("job")
    sdgs = factory.LazyFunction(
        lambda: sorted(
            set(sdg_factory().fuzz() for _ in range(FuzzyInteger(0, 17).fuzz()))
        )
    )

    facebook = factory.Faker("url")
    mobile_phone = factory.Faker("phone_number")
    linkedin = factory.Faker("url")
    medium = factory.Faker("url")
    website = factory.Faker("url")
    personal_email = factory.Faker("email")
    skype = factory.Faker("user_name")
    landline_phone = factory.Faker("phone_number")
    twitter = factory.Faker("url")

    class Meta:
        model = ProjectUser
        django_get_or_create = ("email",)

    # https://factoryboy.readthedocs.io/en/stable/recipes.html#simple-many-to-many-relationship
    @factory.post_generation
    def groups(self, create, extracted, **kwargs):
        if not create:
            return
        self.groups.add(*[get_default_group(), *(extracted if extracted else [])])

    @factory.post_generation
    def publication_status(self, create, extracted, **kwargs):
        if not create:
            return
        publication_status = (
            extracted if extracted else PrivacySettings.PrivacyChoices.PUBLIC
        )
        self.privacy_settings.publication_status = publication_status
        self.privacy_settings.save()

    @factory.post_generation
    def keycloak_account(self, create, extracted, **kwargs):
        if create:
            KeycloakAccountFactory(
                user=self,
                username=self.email,
                email=self.email,
            )


class SeedUserFactory(UserFactory):
    email = factory.LazyAttribute(
        lambda _: f"user-{uuid.uuid4()}@{faker.domain_name()}".lower()
    )

    @factory.post_generation
    def keycloak_account(self, create, extracted, **kwargs):
        if create:
            password = extracted.get("password") if extracted else faker.password()
            email_verified = extracted.get("email_verified") if extracted else False
            KeycloakService.create_user(self, password, email_verified=email_verified)


class UserScoreFactory(factory.django.DjangoModelFactory):
    user = factory.LazyFunction(
        lambda: UserFactory()
    )  # Subfactory seems to not trigger `create()`
    completeness = factory.Faker("pyfloat", positive=True)
    activity = factory.Faker("pyfloat", positive=True)
    score = factory.Faker("pyfloat", positive=True)

    class Meta:
        model = UserScore


class PeopleGroupFactory(factory.django.DjangoModelFactory):
    organization = factory.SubFactory(
        "apps.organizations.factories.OrganizationFactory"
    )
    description = factory.Faker("text")
    email = factory.Faker("email")
    name = factory.Faker("company")
    publication_status = PeopleGroup.PublicationStatus.PUBLIC

    class Meta:
        model = PeopleGroup

    @classmethod
    def create(cls, **kwargs):
        instance = super().create(**kwargs)
        instance.setup_permissions()
        instance.organization.setup_permissions()
        return instance

    @factory.post_generation
    def with_leader(self, create, extracted, **kwargs):
        if create and extracted is True:
            UserFactory(groups=[self.get_leaders()])
