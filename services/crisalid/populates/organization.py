from services.crisalid.models import AuthorityOrganization, Identifier
from services.crisalid.populates.identifier import PopulateIdentifier

from .base import AbstractPopulate
from .logger import logger


class PopulateAuthorityOrganization(AbstractPopulate):
    """Populate authority organizations (documents affiliations) from crisalid
    "authorityOrganizations" query (no relations)
    """

    def __init__(self, *ar, populate_identifiers=None, **kw):
        super().__init__(*ar, **kw)
        self.populate_identifiers = populate_identifiers or PopulateIdentifier(
            self.config, self.cache
        )

    def sanitize_organization_type(self, data: str | None) -> str:
        """Check authority organization type, and return empty value if is not set in enum"""
        if not data:
            return ""
        if data in AuthorityOrganization.OrganizationType:
            return data
        logger.warning("Authority organization type %r not found", data)
        return ""

    def node(self, data: dict) -> AuthorityOrganization | None:
        uid = self.sanitize_string(data.get("uid"))
        if not uid:
            return None
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
        return organization
