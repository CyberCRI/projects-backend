from services.crisalid.models import (
    AuthorityOrganization,
    AuthorityOrganizationIdentifier,
)

from .base import AbstractPopulate
from .logger import logger


class PopulateAuthorityOrganization(AbstractPopulate):
    """Populate authority organizations (documents affiliations) from crisalid
    "authorityOrganizations" query (no relations)
    """

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
        identifiers = self.sanitize_identifiers(
            AuthorityOrganizationIdentifier, data.get("identifiers")
        )
        # uids can be the same in two crisalid instances, organizations are matched by identifiers
        if not identifiers:
            logger.warning("Authority organization %r without identifiers", uid)
            return None

        organization = self.cache.from_identifiers(AuthorityOrganization, identifiers)
        names = [name for name in data.get("display_names") or [] if name]
        self.cache.save(
            organization,
            name=self.sanitize_string(names[0] if names else uid),
            type=self.sanitize_organization_type(data.get("type")),
        )
        self.save_identifiers(organization, identifiers)
        return organization
