import factory
from factory.fuzzy import FuzzyChoice
from faker import Faker

from apps.accounts.factories import UserFactory
from apps.organizations.factories import OrganizationFactory
from services.crisalid import relators

from .models import (
    CrisalidConfig,
    Document,
    DocumentContributor,
    Identifier,
    Researcher,
)

faker = Faker()


class IdentifierFactory(factory.django.DjangoModelFactory):
    harvester = Identifier.Harvester.EPPN

    class Meta:
        model = Identifier

    @factory.lazy_attribute
    def value(self):
        return {
            Identifier.Harvester.HAL: faker.unique.url(),
            Identifier.Harvester.SCANR: faker.unique.url(),
            Identifier.Harvester.OPENALEX: faker.unique.url(),
            Identifier.Harvester.IDREF: faker.unique.uuid4(),
            Identifier.Harvester.SCOPUS: faker.unique.uuid4(),
            Identifier.Harvester.ORCID: faker.unique.uuid4(),
            Identifier.Harvester.LOCAL: faker.unique.uuid4(),
            Identifier.Harvester.EPPN: faker.unique.email(),
            Identifier.Harvester.DOI: faker.unique.doi(),
            Identifier.Harvester.PMID: faker.unique.url(),
        }[self.harvester]


class ResearcherFactory(factory.django.DjangoModelFactory):
    user = factory.LazyFunction(lambda: UserFactory())
    given_name = faker.first_name()
    family_name = faker.last_name()

    class Meta:
        model = Researcher

    @factory.post_generation
    def identifiers(self, create, extracted, **kwargs):
        if not create:
            return
        self.identifiers.set(
            IdentifierFactory(harvester=harvester.value)
            for harvester in Identifier.Harvester
        )


class DocumentFactory(factory.django.DjangoModelFactory):
    title = faker.sentence(nb_words=5)
    description = faker.text()
    publication_date = faker.date_time()
    document_type = FuzzyChoice(
        Document.DocumentType.choices, getter=lambda obj: obj[0]
    )

    class Meta:
        model = Document

    @factory.post_generation
    def identifiers(self, create, extracted, **kwargs):
        if not create:
            return
        self.identifiers.set(
            IdentifierFactory(harvester=harvester.value)
            for harvester in Identifier.Harvester
        )


class DocumentContributorFactory(factory.django.DjangoModelFactory):
    roles = FuzzyChoice(relators.choices, getter=lambda obj: obj[0])
    document = factory.LazyFunction(lambda: DocumentFactory())
    researcher = factory.LazyFunction(lambda: ResearcherFactory())

    class Meta:
        model = DocumentContributor


class CrisalidConfigFactory(factory.django.DjangoModelFactory):
    organization = factory.LazyFunction(lambda: OrganizationFactory())
    crisalidbus_url = faker.url()
    crisalidbus_username = faker.user_name()
    crisalidbus_password = faker.password()
    apollo_url = faker.url()
    apollo_token = faker.password()
    active = True

    class Meta:
        model = CrisalidConfig
