from services.crisalid.models import Structure, StructureIdentifier, StructureRelation
from services.crisalid.utils.structures import sync_structures, with_ancestors

from .base import AbstractPopulate
from .logger import logger

# neo4j labels from crisalid (field "types") to structure main mission
MISSION_FROM_TYPES = {
    "ResearchUnit": Structure.MissionType.RESEARCH,
    "SupportUnit": Structure.MissionType.SCIENTIFIC_SERVICES,
    "AdministrativeUnit": Structure.MissionType.ADMINISTRATIVE_SERVICES,
    "TeachingUnit": Structure.MissionType.TEACHING,
}

RELATIONS_CONNECTIONS = {
    "part_ofConnection": StructureRelation.RelationType.PART_OF,
    "member_ofConnection": StructureRelation.RelationType.MEMBER_OF,
}


class PopulateStructure(AbstractPopulate):
    """Populate structures from crisalid "organizationUnits" query
    with relations to other structures (part_of / member_of)
    """

    def sanitize_generic_type(self, value: str) -> str | None:
        value = self.sanitize_string(value).lower()
        if value not in Structure.GenericType:
            return None
        return value

    def sanitize_main_mission(self, types: list[str]) -> str:
        for structure_type in types or []:
            if structure_type in MISSION_FROM_TYPES:
                return MISSION_FROM_TYPES[structure_type].value
        return ""

    def node(self, data: dict) -> Structure | None:
        uid = self.sanitize_string(data.get("uid"))
        generic_type = self.sanitize_generic_type(data.get("generic_type"))
        identifiers = self.sanitize_identifiers(
            StructureIdentifier, data.get("identifiers")
        )
        if not all((uid, generic_type, identifiers)):
            logger.error(
                "Invalid Structure: uid=%s generic_type=%s identifiers=%s",
                repr(uid),
                repr(data.get("generic_type")),
                identifiers,
            )
            return None

        # uids can be the same in two crisalid instances, structures are matched by identifiers
        structure = self.cache.from_identifiers(
            Structure, identifiers, organization=self.config.organization
        )
        self.cache.save(
            structure,
            generic_type=generic_type,
            national_type=self.sanitize_string(data.get("national_type")),
            main_mission=self.sanitize_main_mission(data.get("types")),
            # use acronym or uid if structure doesn't have long label
            name=self.sanitize_languages(data.get("long_labels"))
            or self.sanitize_languages(data.get("short_labels"))
            or uid,
            acronym=self.sanitize_languages(data.get("short_labels")),
            description=self.sanitize_languages(data.get("descriptions")),
            external=bool(data.get("external")),
        )
        self.save_identifiers(structure, identifiers)
        return structure

    def relations(self, structure: Structure, data: dict) -> list[Structure]:
        """recreate relations from the structure to others structures (graph is the source of truth)

        :return: structures whose groups must be synced
        """
        # old ancestors lose the members of this structure if it is moved
        touched = [structure, *structure.ancestors()]

        relations = []
        for connection, relation_type in RELATIONS_CONNECTIONS.items():
            for edge in data.get(connection, {}).get("edges", []):
                related_structure = self.node(edge["node"])
                if related_structure is None:
                    continue

                properties = edge.get("properties") or {}
                relations.append(
                    StructureRelation(
                        structure=structure,
                        related_structure=related_structure,
                        relation_type=relation_type,
                        position=self.sanitize_string(properties.get("position")),
                        start_date=self.sanitize_date(properties.get("start_date")),
                        end_date=self.sanitize_date(properties.get("end_date")),
                    )
                )
                touched.append(related_structure)

        self.replace_relations(structure.relations.all(), relations)
        return touched

    def single(self, data: dict) -> Structure | None:
        structure = self.node(data)
        if structure is not None:
            sync_structures(with_ancestors(self.relations(structure, data)))
        return structure

    def multiple(self, datas: list) -> list[Structure]:
        """groups are synced once, after all structures"""
        structures, touched = [], []
        for data in datas:
            structure = self.node(data)
            if structure is not None:
                structures.append(structure)
                touched.extend(self.relations(structure, data))

        # members of these structures are also members of their ancestors groups
        sync_structures(with_ancestors(touched))
        return structures
