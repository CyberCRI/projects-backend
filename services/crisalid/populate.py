import abc
import datetime
import logging
from functools import cache

from django.contrib.postgres.aggregates.general import ArrayAgg

from services.crisalid.models import Document, DocumentSource, Identifier, Researcher

logger = logging.getLogger(__name__)


class _NOSET:
    pass


CRISALID_FORMAT_DATE = (
    "%Y-%m-%d",
    "%Y-%m",
    "%Y",
)


class AbstractPopulate(abc.ABC):
    def __init__(self, cache_dict_model=None, identiers=None):
        # cache the methods to avoid mem leak and optimize the get/create
        self.cache_dict_model = cache_dict_model or cache(self.cache_dict_model)
        self.cache_identifiers = identiers or {
            f"{o.harvester}::{o.value}": o.pk for o in Identifier.objects.all()
        }

    def save_if_needed(self, model, **fields):
        updated = False
        for field, value in fields.items():
            if getattr(model, field, _NOSET) == value:
                continue

            setattr(model, field, value)
            updated = True

        if updated or not model.pk:
            logger.debug("Save model %s", model)
            model.save()

    def cache_dict_model(self, model):
        qs = model.objects.all()
        if model is Researcher:
            qs = qs.annotate(identifiers_lst_pk=ArrayAgg("identifiers__m2m"))
        elif model is Document:
            qs = qs.annotate(authors_lst_pk=ArrayAgg("authors__m2m"))
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
        needed_pk = sorted(objs_toadd)
        actual = sorted(getattr(obj, key))
        if needed_pk != actual:
            setattr(obj, key, needed_pk)
            getattr(obj, key.removesuffix("__m2m")).set(needed_pk)

    @abc.abstractmethod
    def single(self, data):
        raise NotImplemented

    def multiple(self, datas: list) -> list:
        return [self.single(data) for data in datas]


class PopulateResearcher(AbstractPopulate):
    def single(self, user: dict) -> Researcher:
        researcher = self.cache_model(Researcher, crisalid_uid=user["uid"])
        self.save_if_needed(researcher, display_name=user["display_name"])

        user_identifiers = []
        for iden in user["identifiers"]:
            identifier_id = self.cache_identifier(
                value=iden["value"],
                harvester=iden["type"].lower(),
            )
            user_identifiers.append(identifier_id)

        self.save_if_needed(researcher)
        self.save_m2m_if_needed(researcher, "identifiers__m2m", user_identifiers)

        return researcher


class PopulateDocumentCrisalid(AbstractPopulate):
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
        if value is None:
            return None

        for format_date in CRISALID_FORMAT_DATE:
            try:
                return datetime.datetime.strptime(value, format_date).date()
            except (TypeError, ValueError):
                continue

        logger.error("Invalid date format %s", value)
        raise ValueError(f"invalid date {value}")

    def single(self, data: dict):
        """this method create/update only on documents from crisalid"""

        document = self.cache_model(Document, crisalid_uid=data["uid"])
        self.save_if_needed(
            document,
            title=self.sanitize_languages(data["titles"]),
            publication_date=self.sanitize_date(data["publication_date"]),
        )

        for recorded in data["recorded_by"]:
            identifier_id = self.cache_identifier(
                value=recorded["uid"],
                harvester=recorded["harvester"].lower(),
            )

            doc_sources = self.cache_model(DocumentSource, crisalid_uid=recorded["uid"])
            self.save_if_needed(
                doc_sources,
                identifier_id=identifier_id,
                document=document,
                document_type=None,
            )

            harvested_for = self.populate_researcher.multiple(recorded["harvested_for"])
            self.save_m2m_if_needed(
                document, "authors__m2m", (o.pk for o in harvested_for)
            )
