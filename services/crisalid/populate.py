import abc
import datetime
from functools import cache

from services.crisalid.models import Document, DocumentSource, Identifier, Researcher


class AbstractPopulate(abc.ABC):
    def __init__(self, cache_model=None):
        # cache the methods to avoid mem leak and optimize the get/create
        self.cache_model = cache_model or cache(self.cache_model)

    def save_if_needed(self, model, **fields):
        updated = False
        for field, value in fields.items():
            if hasattr(model, field) and getattr(model, field) == value:
                continue
            setattr(model, field, value)
            updated = True
        if updated or not model.pk:
            model.save()

    def cache_model(self, model, **fields):
        """cache same models to optimzie bd requests/create"""
        try:
            return model.objects.get(**fields)
        except model.DoesNotExist:
            return model(**fields)

    @abc.abstractmethod
    def single(self, data):
        raise NotImplemented

    def multiple(self, datas: list) -> list:
        objs = []
        for data in datas:
            objs.append(self.single(data))
        return objs


class PopulateResearcher(AbstractPopulate):
    def single(self, user: dict) -> Researcher:
        researcher = self.cache_model(Researcher, crisalid_uid=user["uid"])
        self.save_if_needed(researcher, display_name=user["display_name"])

        user_identifiers = []
        for iden in user["identifiers"]:
            id_researcher = self.cache_model(
                Identifier,
                value=iden["value"],
                harvester=iden["type"].lower(),
            )
            self.save_if_needed(id_researcher)
            user_identifiers.append(id_researcher)

        self.save_if_needed(researcher)
        researcher.identifiers.set(user_identifiers)

        return researcher


class PopulateDocumentCrisalid(AbstractPopulate):
    def __init__(self):
        super().__init__()
        self.populate_researcher = PopulateResearcher(self.cache_model)

    def sanitize_languages(self, values: list[dict[str, str]]) -> str:
        """convert languages choices from crisalid fields
        crisalid return a list of objects with "language" and "value" assosiated from the language
        this method return the best choices from getting value
        """
        maps_languages = {}

        for value in values:
            maps_languages[value["language"]] = value["value"]

        if not maps_languages:
            return ""

        return (
            maps_languages.get("en")
            or maps_languages.get("fr")
            or next(iter(maps_languages.values()))
        )

    def sanitize_date(self, value: str | None) -> datetime.datetime | None:
        """this method convert datetime string from crisalid to python datetime
        some date from crisalid as diferent format
        """
        FORMAT_DATE = (
            "%Y-%m-%d",
            "%Y-%m",
            "%Y",
        )
        if value is None:
            return None

        for format_date in FORMAT_DATE:
            try:
                return datetime.datetime.strptime(value, format_date)
            except (TypeError, ValueError):
                continue
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
            identifier = self.cache_model(
                Identifier,
                value=recorded["uid"],
                harvester=recorded["harvester"].lower(),
            )
            self.save_if_needed(identifier)

            doc_sources = self.cache_model(DocumentSource, crisalid_uid=recorded["uid"])
            self.save_if_needed(
                doc_sources,
                identifier=identifier,
                document=document,
                document_type=None,
            )

            harvested_for = self.populate_researcher.multiple(recorded["harvested_for"])
            document.authors.set(harvested_for)
