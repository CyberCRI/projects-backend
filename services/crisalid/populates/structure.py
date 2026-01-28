from services.crisalid.models import Structure
from services.crisalid.populates.identifier import PopulateIdentifier

from .base import AbstractPopulate


class PopulateStructure(AbstractPopulate):
    """Populate class for structure element

    ex:
    {
        "acronym": "CES",
        "types": [
          "Organisation",
          "ResearchStructure"
        ],
        "names": [
          {
            "language": "fr",
            "value": "UMR 8174 - CES"
          }
        ],
        "identifiers": [
          {
            "type": "RNSR",
            "value": "200612823S"
          },
          {
            "type": "local",
            "value": "U02C"
          }
        ]
      }
    """

    def __init__(self, *ar, populate_identifiers=None, **kw):
        super().__init__(*ar, **kw)
        self.populate_identifiers = populate_identifiers or PopulateIdentifier(
            self.config, self.cache
        )

    def single(self, data: dict) -> Structure | None:
        acronym = self.sanitize_string(data["acronym"])
        name = self.sanitize_languages(data["names"])
        identifiers = self.populate_identifiers.multiple(data["identifiers"])

        # no create structure if no identifiers are set
        if not identifiers:
            return None

        structure = self.cache.from_identifiers(Structure, identifiers)
        self.cache.save(
            structure, acronym=acronym, name=name, organization=self.config.organization
        )
        self.cache.save_m2m(structure, identifiers=identifiers)

        return structure
