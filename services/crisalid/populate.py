import abc
import datetime
import logging
from functools import cache

from django.contrib.postgres.aggregates.general import ArrayAgg

from apps.accounts.models import ProjectUser
from services.crisalid import relators
from services.crisalid.models import (
    Identifier,
    Publication,
    PublicationContributor,
    Researcher,
)

logger = logging.getLogger(__name__)


# create unique obj
class _NOSET:
    pass


CRISALID_FORMAT_DATE = ("%Y-%m-%d", "%Y-%m", "%Y")


class AbstractPopulate(abc.ABC):
    def __init__(self, cache_dict_model=None, identiers=None, contributors=None):
        # cache the methods to avoid mem leak and optimize the get/create
        self.cache_dict_model = cache_dict_model or cache(self.cache_dict_model)

        self.cache_identifiers = identiers or {
            f"{o.harvester}::{o.value}": o.pk for o in Identifier.objects.all()
        }
        self.cache_contributors = contributors or {
            f"{o.publication_id}::{o.researcher_id}": o
            for o in PublicationContributor.objects.all()
        }

    def save_if_needed(self, obj, **fields):
        """check if obj are changed"""
        updated = False
        for field, value in fields.items():
            if getattr(obj, field, _NOSET) == value:
                continue

            setattr(obj, field, value)
            updated = True

        if updated or not obj.pk:
            logger.debug("Save object %s", obj)
            obj.save()

    def cache_dict_model(self, model):
        qs = model.objects.all()
        if model is Researcher:
            qs = qs.select_related("user").annotate(
                identifiers_m2m_pk=ArrayAgg("identifiers__pk")
            )
        elif model is Publication:
            qs = qs.annotate(
                identifiers_m2m_pk=ArrayAgg("identifiers__pk"),
            )
        return {o.crisalid_uid: o for o in qs}

    def cache_model(self, model, crisalid_uid):
        mapping = self.cache_dict_model(model)
        try:
            return mapping[crisalid_uid]
        except KeyError:
            obj = model(crisalid_uid=crisalid_uid)
            mapping[crisalid_uid] = obj
            return obj

    def cache_identifier(self, value, harvester):
        k = f"{harvester}::{value}"
        try:
            return self.cache_identifiers[k]
        except KeyError:
            obj = Identifier(value=value, harvester=harvester)
            self.save_if_needed(obj)
            self.cache_identifiers[k] = obj.pk
            return obj.pk

    def cache_contributor(self, publication, researcher):
        k = f"{publication.id}::{researcher.id}"
        try:
            return self.cache_contributors[k]
        except KeyError:
            obj = PublicationContributor(publication=publication, researcher=researcher)
            self.save_if_needed(obj)
            self.cache_identifiers[k] = obj.pk
            return obj

    def save_m2m_if_needed(self, obj, key, objs_toadd: list[int]) -> False:
        """this method checks all pk m2m linked to the obj, if is a diff, we "set" all needed_pk"""
        needed_pk = sorted(objs_toadd)
        actual = sorted(getattr(obj, key, []))
        if needed_pk != actual:
            getattr(obj, key.removesuffix("_m2m_pk")).clear()
            getattr(obj, key.removesuffix("_m2m_pk")).set(needed_pk)
            setattr(obj, key, needed_pk)

    def sanitize_languages(self, values: list[dict[str, str]]) -> str:
        """convert languages choices from crisalid fields
        crisalid return a list of objects with "language" and "value" assosiated from the language
        this method return the best choices from getting value
        """
        if not values:
            return ""

        maps_languages = {}
        for value in values:
            maps_languages[value["language"]] = value["value"]

        return (
            maps_languages.get("en")
            or maps_languages.get("fr")
            or next(iter(maps_languages.values()))
        )

    @abc.abstractmethod
    def single(self, data):
        raise NotImplementedError

    def multiple(self, datas: list) -> list:
        return [self.single(data) for data in datas]


class PopulateResearcher(AbstractPopulate):
    def get_names(self, data):
        given_name = data.get("first_names")
        family_name = data.get("last_names")
        # "name" from apollo return list with languages
        if data["names"]:
            given_name = self.sanitize_languages(data["names"][0]["first_names"])
            family_name = self.sanitize_languages(data["names"][0]["last_names"])

        return given_name, family_name

    def check_mapping_user(
        self, researcher: Researcher, data: dict
    ) -> ProjectUser | None:
        """match user from researcher (need eppn)"""

        if researcher.user:
            return researcher.user

        for iden in data["identifiers"]:
            if iden["type"].lower() != Identifier.Harvester.EPPN.value:
                continue
            user = ProjectUser.objects.filter(email=iden["value"]).first()
            if user is not None:
                return user

            given_name, family_name = self.get_names(data)
            return ProjectUser.objects.create(
                email=iden["value"], given_name=given_name, family_name=family_name
            )
        return None

    def single(self, data: dict) -> Researcher:
        researcher = self.cache_model(Researcher, crisalid_uid=data["uid"])

        user_identifiers = []
        for iden in data["identifiers"]:
            identifier_id = self.cache_identifier(
                value=iden["value"], harvester=iden["type"].lower()
            )
            user_identifiers.append(identifier_id)

        user = self.check_mapping_user(researcher, data)
        self.save_if_needed(researcher, display_name=data["display_name"], user=user)
        self.save_m2m_if_needed(researcher, "identifiers_m2m_pk", user_identifiers)

        return researcher


class PopulatePublication(AbstractPopulate):
    def __init__(self):
        super().__init__()
        self.sanitize_date = cache(self.sanitize_date)
        self.populate_researcher = PopulateResearcher(
            self.cache_dict_model, self.cache_identifiers, self.cache_contributors
        )

    def sanitize_date(self, value: str | None) -> datetime.date | None:
        """this method convert date string from crisalid to python date
        some date from crisalid as diferent format
        """
        if not value:
            return None

        for format_date in CRISALID_FORMAT_DATE:
            try:
                # parse the value and convert it to date
                return datetime.datetime.strptime(value, format_date).date()
            except (TypeError, ValueError):
                continue

        logger.warning("Invalid date format %s", value)
        return None

    def sanitize_publication_type(self, data: str | None):
        if not data:
            return None
        if data in Publication.PublicationType:
            return data
        logger.warning("Publications type %r not found", data)
        return None

    def sanitize_roles(self, data: list[str]) -> list[str]:
        roles = []
        for role in data:
            if role in relators.dict_relators:
                roles.append(relators.dict_relators[role]["value"])
            else:
                logger.warning("Invalid role %s", role)

        return roles

    def single(self, data: dict):
        """this method create/update only on publications from crisalid"""

        publication = self.cache_model(Publication, crisalid_uid=data["uid"])
        self.save_if_needed(
            publication,
            title=self.sanitize_languages(data["titles"]),
            description=self.sanitize_languages(data["abstracts"]),
            publication_date=self.sanitize_date(data["publication_date"]),
            publication_type=self.sanitize_publication_type(data["document_type"]),
        )

        # identifiers (hal, openalex, idref ...ect)
        identifier_ids = []
        for recorded in data["recorded_by"]:
            identifier_id = self.cache_identifier(
                value=recorded["uid"], harvester=recorded["harvester"].lower()
            )
            identifier_ids.append(identifier_id)
        self.save_m2m_if_needed(publication, "identifiers_m2m_pk", identifier_ids)

        contributors = []
        for contribution in data["has_contributions"]:
            for researcher in self.populate_researcher.multiple(
                contribution["contributor"]
            ):

                roles = self.sanitize_roles(contribution["roles"])

                contribution = self.cache_contributor(
                    publication=publication,
                    researcher=researcher,
                )
                self.save_if_needed(contribution, roles=roles)
                contributors.append(contribution)

        return publication
