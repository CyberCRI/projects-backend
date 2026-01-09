from services.crisalid.models import Identifier

from .base import AbstractPopulate


class PopulateIdentifier(AbstractPopulate):
    """Populate class for identifiers element

    ex:
     {
        "type": "RNSR",
        "value": "200612823S"
    }
    """

    def sanitize_harvester(self, harvester: str) -> str:
        # harvester can be "orcid_id" or "orcid"
        if harvester == "orcid_id":
            return Identifier.Harvester.ORCID

        if harvester not in Identifier.Harvester:
            return None

        return harvester

    def single(self, data: dict) -> Identifier | None:
        harvester = self.sanitize_harvester(self.sanitize_string(data["type"]).lower())
        value = self.sanitize_string(data["value"])

        if not all((harvester, value)):
            return None

        identifier = self.cache.model(
            Identifier,
            value=value,
            harvester=harvester,
        )
        self.cache.save(identifier)
        return identifier
