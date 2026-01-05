from apps.accounts.models import ProjectUser
from services.crisalid.models import Identifier, Researcher

from .base import AbstractPopulate


class PopulateResearcher(AbstractPopulate):
    def get_names(self, data):
        given_name = data.get("first_names")
        family_name = data.get("last_names")
        # "name" from apollo return list with languages
        if data.get("names"):
            given_name = self.sanitize_languages(data["names"][0]["first_names"])
            family_name = self.sanitize_languages(data["names"][0]["last_names"])

        return given_name or "", family_name or ""

    def check_mapping_user(
        self, researcher: Researcher, data: dict
    ) -> ProjectUser | None:
        """match user from researcher (need eppn)"""

        if researcher.user:
            return researcher.user

        for iden in data["identifiers"]:
            if iden["type"].lower() != Identifier.Harvester.EPPN.value:
                continue

            # filter by eppn
            user = self.cache.model(ProjectUser, email=iden["value"])

            # create only user if we have eppn
            given_name, family_name = self.get_names(data)
            self.cache.save(
                user,
                email=iden["value"],
                given_name=given_name,
                family_name=family_name,
            )
            return user
        return None

    def single(self, data: dict) -> Researcher:
        researcher = self.cache.model(Researcher, crisalid_uid=data["uid"])

        researcher_identifiers = []
        for iden in data["identifiers"]:
            identifier = self.cache.model(
                Identifier, value=iden["value"], harvester=iden["type"].lower()
            )
            self.cache.save(identifier)
            researcher_identifiers.append(identifier)

        user = self.check_mapping_user(researcher, data)
        self.cache.save(researcher, display_name=data["display_name"], user=user)
        self.cache.save_m2m(researcher, identifiers=researcher_identifiers)

        return researcher
