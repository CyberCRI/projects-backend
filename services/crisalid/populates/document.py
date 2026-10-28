from apps.commons.utils import BeautifulSoupProjects
from services.crisalid import relators
from services.crisalid.models import (
    AuthorityOrganization,
    CrisalidConfig,
    Document,
    DocumentContributor,
    DocumentJournal,
    Identifier,
    Journal,
)
from services.crisalid.populates.identifier import PopulateIdentifier

from .base import AbstractPopulate
from .logger import logger
from .researcher import PopulateResearcher


class PopulateDocument(AbstractPopulate):
    def __init__(self, config: CrisalidConfig, cache=None):
        super().__init__(config, cache)
        self.populate_identifiers = PopulateIdentifier(self.config, self.cache)
        self.populate_researcher = PopulateResearcher(
            self.config,
            self.cache,
            populate_identifiers=self.populate_identifiers,
        )

    def sanitize_document_type(self, data: str | None):
        """Check documentType , and return unknow value if is not set in enum"""
        if data in Document.DocumentType:
            return data
        logger.warning("Document type %r not found", data)
        return Document.DocumentType.UNKNOWN.value

    def sanitize_organization_type(self, data: str | None) -> str:
        """Check authority organization type, and return empty value if is not set in enum"""
        if not data:
            return ""
        if data in AuthorityOrganization.OrganizationType:
            return data
        logger.warning("Authority organization type %r not found", data)
        return ""

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
            data = edge["node"]
            uid = self.sanitize_string(data.get("uid"))
            if not uid:
                continue
            journal = self.cache.model(Journal, uid=uid)
            titles = [title for title in data.get("titles") or [] if title]
            self.cache.save(
                journal, title=self.sanitize_string(titles[0] if titles else uid)
            )

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

    def contributors(self, document: Document, contributions: list[dict]):
        """recreate relations from the document to its contributors"""
        # a researcher can have multiple contributions, roles are merged
        roles = {}
        for contribution in contributions:
            contribution_roles = self.sanitize_roles(contribution["roles"])
            for researcher in self.populate_researcher.multiple(
                contribution["contributor"]
            ):
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

    def affiliations(self, contributions: list[dict]) -> list[AuthorityOrganization]:
        organizations = {}
        for contribution in contributions:
            for data in contribution.get("affiliations") or []:
                uid = self.sanitize_string(data.get("uid"))
                if not uid or uid in organizations:
                    continue
                organization = self.cache.model(AuthorityOrganization, crisalid_uid=uid)
                names = [name for name in data.get("display_names") or [] if name]
                self.cache.save(
                    organization,
                    name=self.sanitize_string(names[0] if names else uid),
                    type=self.sanitize_organization_type(data.get("type")),
                )
                # only keep identifiers known by projects
                identifiers = self.populate_identifiers.multiple(
                    [
                        identifier
                        for identifier in data.get("identifiers") or []
                        if self.sanitize_string(identifier.get("harvester")).lower()
                        in Identifier.Harvester
                    ]
                )
                self.cache.save_m2m(organization, identifiers=identifiers)
                organizations[uid] = organization
        return list(organizations.values())

    def single(self, data: dict) -> Document | None:
        """this method create/update only on document from crisalid"""
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
        self.cache.save_m2m(
            document,
            identifiers=documents_identifiers,
            affiliations=self.affiliations(data["has_contributions"]),
        )
        self.journals(document, data.get("publishedInConnection") or {})
        self.contributors(document, data["has_contributions"])

        return document
