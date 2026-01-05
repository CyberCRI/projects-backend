from services.crisalid import relators
from services.crisalid.models import Document, DocumentContributor, Identifier

from .base import AbstractPopulate
from .logger import logger
from .researcher import PopulateResearcher


class PopulateDocument(AbstractPopulate):
    def __init__(self, cache=None):
        super().__init__(cache)
        self.populate_researcher = PopulateResearcher(self.cache)

    def sanitize_document_type(self, data: str | None):
        """Check documentType , and return unknow value if is not set in enum"""
        if data in Document.DocumentType:
            return data
        logger.warning("Document type %r not found", data)
        return Document.DocumentType.UNKNOWN.value

    def sanitize_roles(self, data: list[str]) -> list[str]:
        """return all roles from relators json"""
        roles = []
        for role in data:
            if role in relators.dict_relators:
                roles.append(relators.dict_relators[role]["value"])
            else:
                logger.warning("Invalid role %s", role)

        return roles

    def single(self, data: dict):
        """this method create/update only on document from crisalid"""

        document = self.cache.model(Document, crisalid_uid=data["uid"])
        self.cache.save(
            document,
            title=self.sanitize_languages(data["titles"]),
            description=self.sanitize_languages(data["abstracts"]),
            publication_date=self.sanitize_date(data["publication_date"]),
            document_type=self.sanitize_document_type(data["document_type"]),
        )

        # identifiers (hal, openalex, idref ...ect)
        identifiers = []
        for recorded in data["recorded_by"]:
            identifier = self.cache.model(
                Identifier,
                value=recorded["uid"],
                harvester=recorded["harvester"].lower(),
            )
            self.cache.save(identifier)
            identifiers.append(identifier)
        self.cache.save_m2m(document, identifiers=identifiers)

        contributors = []
        for contribution in data["has_contributions"]:
            for researcher in self.populate_researcher.multiple(
                contribution["contributor"]
            ):

                roles = self.sanitize_roles(contribution["roles"])

                contribution = self.cache.model(
                    DocumentContributor,
                    document=document,
                    researcher=researcher,
                )
                self.cache.save(contribution, roles=roles)
                contributors.append(contribution)

        return document
