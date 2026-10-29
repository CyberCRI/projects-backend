from apps.accounts.models import PrivacySettings, ProjectUser
from services.crisalid.models import (
    Identifier,
    Researcher,
    ResearcherStructure,
    Structure,
)
from services.crisalid.populates.identifier import PopulateIdentifier
from services.crisalid.utils.structures import sync_group_members, with_ancestors

from .base import AbstractPopulate
from .logger import logger

STRUCTURES_CONNECTIONS = {
    "membershipsConnection": ResearcherStructure.RelationType.MEMBERSHIP,
    "employmentsConnection": ResearcherStructure.RelationType.EMPLOYMENT,
}


class PopulateResearcher(AbstractPopulate):
    def __init__(self, *ar, populate_identifiers=None, **kw):
        super().__init__(*ar, **kw)
        self.populate_identifiers = populate_identifiers or PopulateIdentifier(
            self.config, self.cache
        )

    def get_names(self, data):
        given_name = family_name = ""

        for name in data["names"]:
            given_name = self.sanitize_languages(name["first_names"])
            family_name = self.sanitize_languages(name["last_names"])

        return given_name, family_name

    def create_user(self, eppn: str, given_name: str, family_name: str) -> ProjectUser:
        # filter by eppn
        user = self.cache.model(ProjectUser, email=eppn)

        if not user.pk:
            # create only user if we have eppn
            self.cache.save(
                user, email=eppn, given_name=given_name, family_name=family_name
            )
            # researcher is hidden by default
            self.cache.save(
                user.privacy_settings,
                publication_status=PrivacySettings.PrivacyChoices.ORGANIZATION.value,
            )

        return self.update_user(user)

    def update_user(self, user: ProjectUser) -> ProjectUser:
        group_organization = self.config.organization.get_users()
        user.groups.add(group_organization)

        return user

    def check_mapping_user(
        self,
        researcher: Researcher,
        identifiers: list[Identifier],
        given_name: str,
        family_name: str,
    ) -> ProjectUser | None:
        """match user from researcher (need eppn)"""

        if researcher.user:
            return self.update_user(researcher.user)

        for iden in identifiers:
            if iden.harvester != Identifier.Harvester.EPPN:
                continue

            return self.create_user(iden.value, given_name, family_name)
        return None

    def single(self, data: dict) -> Researcher | None:
        researcher_identifiers = self.populate_identifiers.multiple(data["identifiers"])

        # remove local/eppn identifiers to match only hal/eppn/orcid ..ect
        researcher_identifiers_without_local = [
            identifier
            for identifier in researcher_identifiers
            if identifier.harvester not in Researcher.PRIVACY_HARVESTER
        ]

        # researcher withtout any identifiers no neeeeeeed to be created
        if not researcher_identifiers_without_local:
            return None

        researcher = self.cache.from_identifiers(
            Researcher, researcher_identifiers_without_local
        )

        given_name, family_name = self.get_names(data)
        user = self.check_mapping_user(
            researcher, researcher_identifiers, given_name, family_name
        )

        self.cache.save(
            researcher,
            given_name=given_name,
            family_name=family_name,
            user=user,
        )
        self.cache.save_m2m(researcher, identifiers=researcher_identifiers)

        # researchers from documents contributions don't have structures data
        if any(connection in data for connection in STRUCTURES_CONNECTIONS):
            self.structures(researcher, data)

        return researcher

    def structures(self, researcher: Researcher, data: dict):
        """recreate relations from researcher to structures of the organization (graph is the source of truth)"""
        edges = [
            (edge, relation_type)
            for connection, relation_type in STRUCTURES_CONNECTIONS.items()
            for edge in data.get(connection, {}).get("edges", [])
        ]

        structures = {
            structure.crisalid_uid: structure
            for structure in Structure.objects.filter(
                organization=self.config.organization,
                crisalid_uid__in={edge["node"]["uid"] for edge, _ in edges},
            )
        }
        # structures with old relations, to sync their members
        touched_structures = set(
            Structure.objects.filter(
                organization=self.config.organization,
                researcherstructure__researcher=researcher,
            )
        )

        relations = []
        for edge, relation_type in edges:
            uid = edge["node"]["uid"]
            structure = structures.get(uid)
            if structure is None:
                logger.warning(
                    "Structure %s not found for %s %s", uid, relation_type, researcher
                )
                continue

            properties = edge.get("properties") or {}
            relations.append(
                ResearcherStructure(
                    researcher=researcher,
                    structure=structure,
                    relation_type=relation_type,
                    position_code=self.sanitize_string(properties.get("position_code")),
                    start_date=self.sanitize_date(properties.get("start_date")),
                    end_date=self.sanitize_date(properties.get("end_date")),
                )
            )
            touched_structures.add(structure)

        self.replace_relations(
            ResearcherStructure.objects.filter(
                researcher=researcher, structure__organization=self.config.organization
            ),
            relations,
        )

        # researchers are members of structures groups and their ancestors groups
        for structure in with_ancestors(touched_structures):
            sync_group_members(structure)
