import abc
import datetime
from typing import TypeVar

from services.crisalid.models import CrisalidConfig

from .caches import BaseCache, LiveCache
from .logger import logger

CRISALID_FORMAT_DATE = ("%Y-%m-%d", "%Y-%m", "%Y")


TCACHE = TypeVar("TCACHE", bound=BaseCache)


class AbstractPopulate(metaclass=abc.ABCMeta):

    def __init__(self, config: CrisalidConfig, cache: TCACHE = None):
        self.config = config
        self.cache = cache or LiveCache()

    def sanitize_languages(self, values: list[dict[str, str]]) -> str:
        """convert languages choices from crisalid fields
        crisalid return a list of objects with "language" and "value" assosiated from the language
        this method return the best choices from getting value
        """
        if not values:
            return ""

        maps_languages = {}
        for value in values:
            maps_languages[value["language"]] = (value["value"] or "").strip()

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

    @abc.abstractmethod
    def single(self, data):
        raise NotImplementedError

    def multiple(self, datas: list) -> list:
        """return all objects create"""
        final = []
        for data in datas:
            el = self.single(data)
            if el is not None:
                final.append(el)
        return final
