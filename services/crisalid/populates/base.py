import abc
import datetime
from typing import TypeVar

from django.db import models, transaction

from services.crisalid.models import AbstractIdentifier, CrisalidConfig
from services.crisalid.utils.identifiers import link_identifiers, release_identifiers

from .caches import BaseCache, LiveCache
from .logger import logger

CRISALID_FORMAT_DATE = ("%Y-%m-%d", "%Y-%m", "%Y")


TCACHE = TypeVar("TCACHE", bound=BaseCache)


class AbstractPopulate(metaclass=abc.ABCMeta):
    def __init__(self, config: CrisalidConfig, cache: TCACHE = None):
        self.config = config
        self.cache = cache or LiveCache()

    def sanitize_string(self, value) -> str:
        """strip value and convert it to string"""
        if not value:
            return ""
        return str(value).strip()

    def sanitize_languages(self, values: list[dict[str, str]]) -> str:
        """convert languages choices from crisalid fields
        crisalid return a list of objects with "language" and "value" assosiated from the language
        this method return the best choices from getting value
        """
        if not values:
            return ""

        maps_languages = {}
        for value in values:
            maps_languages[value["language"]] = self.sanitize_string(value["value"])

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

        value = value.strip()
        for format_date in CRISALID_FORMAT_DATE:
            try:
                # parse the value and convert it to date
                return datetime.datetime.strptime(value, format_date).date()
            except (TypeError, ValueError):
                continue

        logger.warning("Invalid date format %s", value)
        return None

    def sanitize_identifiers(
        self, identifier_model: type[AbstractIdentifier], datas: list[dict] | None
    ) -> list[dict]:
        """identifiers ({"harvester", "value"}) with a harvester known by the identifier model"""
        identifiers = {}
        for data in datas or []:
            harvester = self.sanitize_string(data.get("harvester")).lower()
            value = self.sanitize_string(data.get("value"))
            if harvester not in identifier_model.Harvester or not value:
                logger.warning(
                    "Invalid %s: harvester=%r value=%r",
                    identifier_model.__name__,
                    harvester,
                    value,
                )
                continue
            identifiers[(harvester, value)] = {"harvester": harvester, "value": value}
        return list(identifiers.values())

    def save_identifiers(self, instance: models.Model, identifiers: list[dict]):
        """identifiers are owned by the instance and linked to the configs sending them:
        - missing ones are created, existing ones are linked to this config
        - the ones no longer sent by this config are unlinked from it
          (and deleted if no config is left)
        """
        manager = instance.identifiers
        expected = {(i["harvester"], i["value"]) for i in identifiers}
        existing = {(i.harvester, i.value): i.pk for i in manager.all()}
        with transaction.atomic():
            release_identifiers(
                manager.exclude(
                    pk__in=[pk for key, pk in existing.items() if key in expected]
                ),
                self.config,
            )
            created = manager.model.objects.bulk_create(
                manager.model(
                    **{manager.field.name: instance}, harvester=harvester, value=value
                )
                for harvester, value in expected - existing.keys()
            )
            link_identifiers(
                manager.model,
                [pk for key, pk in existing.items() if key in expected]
                + [identifier.pk for identifier in created],
                self.config,
            )

    def replace_relations(self, queryset: models.QuerySet, relations: list):
        """the graph is the source of truth: relations are deleted and recreated"""
        with transaction.atomic():
            queryset.delete()
            queryset.model.objects.bulk_create(relations)

    @abc.abstractmethod
    def node(self, data):
        """create/update the object only (used for related objects missing in the database)"""
        raise NotImplementedError

    def relations(self, instance, data: dict):
        """create/update the relations owned by the object
        related objects missing in the database are created (node only, never their relations)
        """
        return

    def single(self, data):
        """create/update the object and its relations"""
        instance = self.node(data)
        if instance is not None:
            self.relations(instance, data)
        return instance

    def multiple(self, datas: list) -> list:
        """return all objects create"""
        final = []
        for data in datas:
            el = self.single(data)
            if el is not None:
                final.append(el)
        return final
