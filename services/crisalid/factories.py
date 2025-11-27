import factory
from apps.accounts.factories import UserFactory
from apps.organizations.factories import OrganizationFactory
from factory.fuzzy import FuzzyChoice
from faker import Faker

from services.crisalid import relators

from .models import (
    CrisalidConfig,
    Document,
    DocumentContributor,
    Identifier,
    Researcher,
)

faker = Faker()

HAL = "hal"
SCANR = "scanr"
OPENALEX = "openalex"

IDREF = "idref"
SCOPUS = "scopus"
ORCID = "orcid"
LOCAL = "local"
EPPN = "eppn"
DOI = "doi"
PMID = "pmid"


def harvester_values(harvester_type: Identifier.Harvester):
    return {
        Identifier.Harvester.HAL: factory.Faker("url"),
        Identifier.Harvester.SCANR: factory.Faker("url"),
        Identifier.Harvester.OPENALEX: factory.Faker("url"),
        Identifier.Harvester.IDREF: factory.Faker("uuid4"),
        Identifier.Harvester.SCOPUS: factory.Faker("uuid4"),
        Identifier.Harvester.ORCID: factory.Faker("uuid4"),
        Identifier.Harvester.LOCAL: factory.Faker("uuid4"),
        Identifier.Harvester.EPPN: factory.Faker("email"),
        Identifier.Harvester.DOI: factory.Faker("doi"),
        Identifier.Harvester.PMID: factory.Faker("url"),
    }[harvester_type]


class IdentifierFactory(factory.django.DjangoModelFactory):
    harvester = Identifier.Harvester.EPPN
    value = harvester_values(harvester)

    class Meta:
        model = Identifier


class ResearcherFactory(factory.django.DjangoModelFactory):
    crisalid_uid = factory.Faker("uuid4")
    user = factory.LazyFunction(lambda: UserFactory())
    display_name = f"{factory.Faker("first_name")} {factory.Faker("last_name")}"

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
    crisalid_uid = factory.Faker("uuid4")
    title = factory.Faker("sentence", nb_words=5)
    description = factory.Faker("text")
    publication_date = factory.Faker("date_time")
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
    crisalidbus_host = factory.Factory("url")
    crisalidbus_username = factory.Factory("username")
    crisalidbus_password = factory.Factory("password")
    apollo_host = factory.Factory("url")
    apollo_token = factory.Factory("password")
    active = True

    class Meta:
        model = CrisalidConfig
