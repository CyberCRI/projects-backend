from apps.commons.utils import BeautifulSoupProjects
from services.crisalid import relators
from services.crisalid.models import (
    CrisalidConfig,
    Document,
    DocumentContributor,
    DocumentJournal,
)
from services.crisalid.populates.identifier import PopulateIdentifier

from .base import AbstractPopulate
from .journal import PopulateJournal
from .logger import logger
from .organization import PopulateAuthorityOrganization
from .researcher import PopulateResearcher


class PopulateDocument(AbstractPopulate):
    """Populate documents from crisalid "documents" query
    with relations to journals, affiliations (authority organizations) and contributors
    """

    def __init__(self, config: CrisalidConfig, cache=None):
        super().__init__(config, cache)
        self.populate_identifiers = PopulateIdentifier(self.config, self.cache)
        self.populate_researcher = PopulateResearcher(
            self.config,
            self.cache,
            populate_identifiers=self.populate_identifiers,
        )
        self.populate_journal = PopulateJournal(self.config, self.cache)
        self.populate_organization = PopulateAuthorityOrganization(
            self.config, self.cache, populate_identifiers=self.populate_identifiers
        )

    def sanitize_document_type(self, data: str | None):
        """Check documentType , and return unknow value if is not set in enum"""
        if data in Document.DocumentType:
            return data
        logger.warning("Document type %r not found", data)
        return Document.DocumentType.UNKNOWN.value

    def sanitize_roles(self, data: list[str]) -> list[str]:
        """return all roles from relators json"""
        roles = []
        for url_role in data:
            url_role = url_role.lower()
            if url_role in relators.raw:
                roles.append(relators.raw[url_role]["key"])
            else:
                logger.warning("Invalid role %s", url_role)

        return roles

    def sanitize_content(self, content: str) -> str:
        """some text from crisalid is wrapped arround html,
        this method remove html content
        """

        return str(BeautifulSoupProjects(content).text)

    def journals(self, document: Document, connection: dict):
        """recreate relations from the document to journals where it is published"""
        relations = []
        for edge in connection.get("edges", []):
            journal = self.populate_journal.node(edge["node"])
            if journal is None:
                continue

            properties = edge.get("properties") or {}
            relations.append(
                DocumentJournal(
                    document=document,
                    journal=journal,
                    volume=self.sanitize_string(properties.get("volume")),
                    issue=self.sanitize_string(properties.get("issue")),
                    pages=self.sanitize_string(properties.get("pages")),
                )
            )

        self.replace_relations(document.document_journals.all(), relations)

    def affiliations(self, document: Document, contributions: list[dict]):
        """recreate relations from the document to its contributors affiliations"""
        organizations = {}
        for contribution in contributions:
            for data in contribution.get("affiliations") or []:
                organization = self.populate_organization.node(data)
                if organization is not None:
                    organizations[organization.pk] = organization
        self.cache.save_m2m(document, affiliations=list(organizations.values()))

    def contributors(self, document: Document, contributions: list[dict]):
        """recreate relations from the document to its contributors"""
        # a researcher can have multiple contributions, roles are merged
        roles = {}
        for contribution in contributions:
            contribution_roles = self.sanitize_roles(contribution["roles"])
            for data in contribution["contributor"]:
                researcher = self.populate_researcher.node(data)
                if researcher is None:
                    continue
                researcher_roles = roles.setdefault(researcher, [])
                researcher_roles += [
                    role for role in contribution_roles if role not in researcher_roles
                ]

        self.replace_relations(
            document.documentcontributor_set.all(),
            [
                DocumentContributor(
                    document=document, researcher=researcher, roles=researcher_roles
                )
                for researcher, researcher_roles in roles.items()
            ],
        )

    def node(self, data: dict) -> Document | None:
        # identifiers (hal, openalex, idref ...ect)
        documents_identifiers = self.populate_identifiers.multiple(data["recorded_by"])

        # no identifiers for this documents, we ignore it
        if not documents_identifiers:
            return None

        document = self.cache.from_identifiers(Document, documents_identifiers)
        self.cache.save(
            document,
            title=self.sanitize_content(self.sanitize_languages(data["titles"])),
            description=self.sanitize_content(
                self.sanitize_languages(data["abstracts"])
            ),
            publication_date=self.sanitize_date(data["publication_date"]),
            document_type=self.sanitize_document_type(data["document_type"]),
        )
        self.cache.save_m2m(document, identifiers=documents_identifiers)
        return document

    def relations(self, document: Document, data: dict):
        self.journals(document, data.get("publishedInConnection") or {})
        self.affiliations(document, data["has_contributions"])
        self.contributors(document, data["has_contributions"])
