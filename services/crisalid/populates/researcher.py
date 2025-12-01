from apps.accounts.models import PrivacySettings, ProjectUser
from services.crisalid.models import Identifier, Researcher

from .base import AbstractPopulate


class PopulateResearcher(AbstractPopulate):
    def get_names(self, data):
        given_name = family_name = ""

        for name in data["names"]:
            given_name = self.sanitize_languages(name["first_names"])
            family_name = self.sanitize_languages(name["last_names"])

        return given_name or "", family_name or ""

    def create_user(self, eppn: str, given_name: str, family_name: str) -> ProjectUser:

        # filter by eppn
        user = self.cache.model(ProjectUser, email=eppn)

        if not user.pk:
            # create only user if we have eppn
            self.cache.save(
                user,
                email=eppn,
                given_name=given_name,
                family_name=family_name,
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
        self, researcher: Researcher, data: dict
    ) -> ProjectUser | None:
        """match user from researcher (need eppn)"""

        if researcher.user:
            return self.update_user(researcher.user)

        for iden in data["identifiers"]:
            if iden["type"].lower() != Identifier.Harvester.EPPN.value:
                continue

            given_name, family_name = self.get_names(data)
            return self.create_user(iden["value"], given_name, family_name)
        return None

    def single(self, data: dict) -> Researcher | None:
        researcher_identifiers = []
        for iden in data["identifiers"]:
            identifier = self.cache.model(
                Identifier, value=iden["value"], harvester=iden["type"].lower()
            )
            self.cache.save(identifier)
            researcher_identifiers.append(identifier)

        # researcher withtout any identifiers no neeeeeeed to be created
        if not researcher_identifiers:
            return None

        # remove local/eppn identifiers to match only hal/eppn/orcid ..ect
        researcher_identifiers_without_local = [
            identifier
            for identifier in researcher_identifiers
            if identifier.harvester
            not in [Identifier.Harvester.LOCAL, Identifier.Harvester.EPPN]
        ]
        researcher = self.cache.from_identifiers(
            Researcher, researcher_identifiers_without_local
        )

        given_name, family_name = self.get_names(data)
        user = self.check_mapping_user(researcher, data)

        self.cache.save(
            researcher, given_name=given_name, family_name=family_name, user=user
        )
        self.cache.save_m2m(researcher, identifiers=researcher_identifiers)

        return researcher
