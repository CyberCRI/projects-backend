from typing import Optional

from services.crisalid.models import Identifier

from .base import AbstractPopulate
from .logger import logger


class PopulateIdentifier(AbstractPopulate):
    """Populate class for identifiers element

    ex:
     {
        "type": "RNSR",
        "value": "200612823S"
    }
    """

    def sanitize_harvester(self, harvester: str) -> Optional[str]:
        """check if harvester is a valid identifier"""
        if harvester not in Identifier.Harvester:
            return None

        return harvester

    def single(self, data: dict) -> Identifier | None:
        harvester = self.sanitize_harvester(self.sanitize_string(data["type"]).lower())
        value = self.sanitize_string(data["value"])

        if not all((harvester, value)):
            logger.error(
                "Invalid Identifier: harvester=%s value=%s",
                repr(harvester),
                repr(value),
            )
            return None

        identifier = self.cache.model(Identifier, value=value, harvester=harvester)
        self.cache.save(identifier)
        return identifier
