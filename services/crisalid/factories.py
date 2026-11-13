import random

import factory
from factory.fuzzy import FuzzyChoice
from faker import Faker

from apps.accounts.factories import UserFactory
from apps.organizations.factories import OrganizationFactory
from services.crisalid import relators
from services.crisalid.models.award import Award
from services.crisalid.models.document import DocumentJournal
from services.crisalid.models.funding import Funding
from services.crisalid.models.journal import Journal
from services.crisalid.models.patent import Patent, PatentContributor
from services.crisalid.models.teaching import Teaching

from .models import (
    AwardContributor,
    CrisalidConfig,
    Document,
    DocumentContributor,
    Researcher,
    ResearcherStructure,
    Structure,
    StructureRelation,
)

faker = Faker()


def identifier_value(harvester: str) -> str:
    if harvester == "eppn":
        return faker.unique.email()
    return faker.unique.uuid4()


def create_identifiers(instance):
    """one identifier of each harvester for the instance"""
    manager = instance.identifiers
    manager.model.objects.bulk_create(
        manager.model(
            **{manager.field.name: instance},
            harvester=harvester.value,
            value=identifier_value(harvester.value),
        )
        for harvester in manager.model.Harvester
    )


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
        create_identifiers(self)


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
        create_identifiers(self)


class DocumentContributorFactory(factory.django.DjangoModelFactory):
    roles = FuzzyChoice(relators.RolesChoices, getter=lambda obj: obj["o"])
    document = factory.LazyFunction(lambda: DocumentFactory())
    researcher = factory.LazyFunction(lambda: ResearcherFactory())

    class Meta:
        model = DocumentContributor


class JournalFactory(factory.django.DjangoModelFactory):
    title = factory.Faker("company")
    acronym = [faker.sentence(1)]

    class Meta:
        model = Journal


class DocumentJournalFactory(factory.django.DjangoModelFactory):
    document = factory.LazyFunction(lambda: DocumentFactory())
    journal = factory.LazyFunction(lambda: JournalFactory())
    pages = faker.sentences(2)
    volume = faker.sentences(2)
    issue = faker.sentences(2)

    class Meta:
        model = DocumentJournal


class PatentFactory(factory.django.DjangoModelFactory):
    name = faker.sentences(2)
    description = faker.text()
    date = faker.date()
    link = faker.url()

    class Meta:
        model = Patent


class PatentContributorFactory(factory.django.DjangoModelFactory):
    researcher = factory.LazyFunction(lambda: ResearcherFactory())
    patent = factory.LazyFunction(lambda: PatentFactory())

    class Meta:
        model = PatentContributor


class AwardFactory(factory.django.DjangoModelFactory):
    name = faker.sentences(2)
    description = faker.text()

    class Meta:
        model = Award


class TeachingFactory(factory.django.DjangoModelFactory):
    name = faker.sentences(2)
    description = faker.text()
    spec = faker.sentences(2)
    level = faker.sentences(2)
    link = faker.url()
    researcher = factory.LazyFunction(lambda: ResearcherFactory())

    class Meta:
        model = Teaching


class FundingFactory(factory.django.DjangoModelFactory):
    name = faker.sentences(2)
    description = faker.text()
    prices = random.randint(1, 1_000_000_000)
    currency = Funding.Currency.EUR.value
    start_date = faker.date_time()
    end_date = start_date - faker.time_delta()

    class Meta:
        model = Funding


class AwardContributorFactory(factory.django.DjangoModelFactory):
    researcher = factory.LazyFunction(lambda: ResearcherFactory())
    award = factory.LazyFunction(lambda: AwardFactory())
    description = faker.text()
    date = faker.date()
    link = faker.url()

    class Meta:
        model = AwardContributor


class StructureFactory(factory.django.DjangoModelFactory):
    organization = factory.LazyFunction(lambda: OrganizationFactory())
    generic_type = Structure.GenericType.UNIT
    name = factory.Faker("company")
    acronym = factory.Sequence(lambda n: f"LAB{n}")

    class Meta:
        model = Structure


class StructureRelationFactory(factory.django.DjangoModelFactory):
    structure = factory.SubFactory(StructureFactory)
    related_structure = factory.SubFactory(
        StructureFactory, organization=factory.SelfAttribute("..structure.organization")
    )
    relation_type = StructureRelation.RelationType.PART_OF

    class Meta:
        model = StructureRelation


class ResearcherStructureFactory(factory.django.DjangoModelFactory):
    researcher = factory.SubFactory(ResearcherFactory)
    structure = factory.SubFactory(StructureFactory)
    relation_type = ResearcherStructure.RelationType.MEMBERSHIP

    class Meta:
        model = ResearcherStructure


class CrisalidConfigFactory(factory.django.DjangoModelFactory):
    organization = factory.LazyFunction(lambda: OrganizationFactory())
    crisalidbus_url = faker.url()
    crisalidbus_username = faker.user_name()
    crisalidbus_password = faker.password()
    apollo_url = faker.url()
    apollo_token = faker.password()
    active = False

    class Meta:
        model = CrisalidConfig
