import factory
from factory.fuzzy import FuzzyChoice
from faker import Faker

from apps.accounts.factories import UserFactory
from apps.organizations.factories import OrganizationFactory
from services.crisalid import relators
from services.crisalid.models.award import Award
from services.crisalid.models.document import DocumentJournal
from services.crisalid.models.journal import Journal
from services.crisalid.models.patent import Patent

from .models import (
    AwardContributor,
    CrisalidConfig,
    Document,
    DocumentContributor,
    Identifier,
    Researcher,
    ResearcherStructure,
    Structure,
    StructureRelation,
)

faker = Faker()


class IdentifierFactory(factory.django.DjangoModelFactory):
    harvester = Identifier.Harvester.EPPN

    class Meta:
        model = Identifier

    @factory.lazy_attribute
    def value(self):
        default = {
            Identifier.Harvester.IDREF: faker.unique.uuid4(),
            Identifier.Harvester.SCOPUS: faker.unique.uuid4(),
            Identifier.Harvester.ORCID: faker.unique.uuid4(),
            Identifier.Harvester.LOCAL: faker.unique.uuid4(),
            Identifier.Harvester.EPPN: faker.unique.email(),
            Identifier.Harvester.PMID: faker.unique.url(),
        }
        if self.harvester in default:
            return default[self.harvester]
        return faker.unique.url()


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
    roles = FuzzyChoice(relators.RolesChoices, getter=lambda obj: obj["o"])
    document = factory.LazyFunction(lambda: DocumentFactory())
    researcher = factory.LazyFunction(lambda: ResearcherFactory())

    class Meta:
        model = DocumentContributor


class JournalFactory(factory.django.DjangoModelFactory):
    uid = faker.sentences(1)
    title = faker.sentence(1)
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
    researcher = factory.LazyFunction(lambda: ResearcherFactory())

    class Meta:
        model = Patent


class AwardFactory(factory.django.DjangoModelFactory):
    name = faker.sentences(2)
    description = faker.text()
    date = faker.date()
    link = faker.url()

    class Meta:
        model = Award


class AwardContributorFactory(factory.django.DjangoModelFactory):
    researcher = factory.LazyFunction(lambda: ResearcherFactory())
    award = factory.LazyFunction(lambda: AwardFactory())

    class Meta:
        model = AwardContributor


class StructureFactory(factory.django.DjangoModelFactory):
    organization = factory.LazyFunction(lambda: OrganizationFactory())
    crisalid_uid = factory.LazyFunction(lambda: f"local-{faker.unique.uuid4()}")
    generic_type = Structure.GenericType.UNIT
    name = factory.Faker("company")

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
