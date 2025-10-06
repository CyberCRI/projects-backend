import abc
import datetime
import logging
from functools import cache

from django.contrib.postgres.aggregates.general import ArrayAgg

from apps.accounts.models import ProjectUser
from services.crisalid.models import Identifier, Publication, Researcher

logger = logging.getLogger(__name__)


# create unique obj
class _NOSET:
    pass


CRISALID_FORMAT_DATE = ("%Y-%m-%d", "%Y-%m", "%Y")


class AbstractPopulate(abc.ABC):
    def __init__(self, cache_dict_model=None, identiers=None):
        # cache the methods to avoid mem leak and optimize the get/create
        self.cache_dict_model = cache_dict_model or cache(self.cache_dict_model)

        self.cache_identifiers = identiers or {
            f"{o.harvester}::{o.value}": o.pk for o in Identifier.objects.all()
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
            qs = qs.annotate(identifiers_m2m_pk=ArrayAgg("identifiers__pk"))
        elif model is Publication:
            qs = qs.annotate(
                authors_m2m_pk=ArrayAgg("authors__pk"),
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

    def save_m2m_if_needed(self, obj, key, objs_toadd: list[int]) -> False:
        """this method checks all pk m2m linked to the obj, if is a diff, we "set" all needed_pk"""
        needed_pk = sorted(objs_toadd)
        actual = sorted(getattr(obj, key, []))
        if needed_pk != actual:
            setattr(obj, key, needed_pk)
            getattr(obj, key.removesuffix("_m2m_pk")).set(needed_pk)

    @abc.abstractmethod
    def single(self, data):
        raise NotImplementedError

    def multiple(self, datas: list) -> list:
        return [self.single(data) for data in datas]


class PopulateResearcher(AbstractPopulate):
    def check_mapping_user(
        self, researcher: Researcher, data: dict
    ) -> ProjectUser | None:
        # TODO(remi): do mapping beetween researcher and user data from crisalid
        return None

    def single(self, data: dict) -> Researcher:
        researcher = self.cache_model(Researcher, crisalid_uid=data["uid"])
        user = self.check_mapping_user(researcher, data)
        self.save_if_needed(researcher, display_name=data["display_name"], user=user)

        user_identifiers = []
        for iden in data["identifiers"]:
            identifier_id = self.cache_identifier(
                value=iden["value"], harvester=iden["type"].lower()
            )
            user_identifiers.append(identifier_id)

        self.save_if_needed(researcher)
        self.save_m2m_if_needed(researcher, "identifiers_m2m_pk", user_identifiers)

        return researcher


class PopulatePublicationCrisalid(AbstractPopulate):
    def __init__(self):
        super().__init__()
        self.sanitize_date = cache(self.sanitize_date)
        self.populate_researcher = PopulateResearcher(
            self.cache_dict_model, self.cache_identifiers
        )

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
        if data in Publication.PublicationsType:
            return data
        logger.warning("Publications type %r not found", data)
        return None

    def single(self, data: dict):
        """this method create/update only on publications from crisalid"""

        publication = self.cache_model(Publication, crisalid_uid=data["uid"])
        self.save_if_needed(
            publication,
            title=self.sanitize_languages(data["titles"]),
            publication_date=self.sanitize_date(data["publication_date"]),
            publication_type=self.sanitize_publication_type(data["document_type"]),
        )

        identifier_ids = []
        authors = []
        for recorded in data["recorded_by"]:
            identifier_id = self.cache_identifier(
                value=recorded["uid"], harvester=recorded["harvester"].lower()
            )
            identifier_ids.append(identifier_id)

            authors.extend(self.populate_researcher.multiple(recorded["harvested_for"]))

        self.save_m2m_if_needed(publication, "authors_m2m_pk", (o.pk for o in authors))
        self.save_m2m_if_needed(publication, "identifiers_m2m_pk", identifier_ids)

        return publication
