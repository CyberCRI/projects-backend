import requests
from django.conf import settings
from mediawiki import MediaWiki
from rest_framework import status

from .exceptions import UnsupportedWikipediaLanguageError, WikibaseAPIException


class WikipediaService:
    MEDIAWIKI_API_URL = "https://www.wikidata.org/w/api.php"

    @classmethod
    def service(cls, language: str = "en") -> MediaWiki:
        """
        Get the Wikimedia service.
        """
        if language not in settings.REQUIRED_LANGUAGES:
            raise UnsupportedWikipediaLanguageError(language=language)
        if not getattr(cls, f"service_{language}", None):
            setattr(cls, f"service_{language}", MediaWiki(lang=language))
        return getattr(cls, f"service_{language}")

    @classmethod
    def autocomplete(cls, query: str, language: str = "en", limit: int = 5) -> list:
        """
        Get the autocomplete data from the Wikimedia API.
        """
        return cls.service(language).prefixsearch(query, results=limit)

    @classmethod
    def wbsearchentities(
        cls, query: str, language: str, limit: int, offset: int
    ) -> list:
        """
        Get the data from the Wikimedia API.
        """
        params = {
            "action": "wbsearchentities",
            "type": "item",
            "format": "json",
            "search": query,
            "language": language,
            "uselang": language,
            "limit": limit,
            "continue": offset,
        }
        return requests.get(cls.MEDIAWIKI_API_URL, params)

    @classmethod
    def wbgetentities(cls, wikipedia_qid: str) -> list:
        """
        Get the data from the Wikimedia API.
        """
        params = {"action": "wbgetentities", "format": "json", "ids": [wikipedia_qid]}
        return requests.get(cls.MEDIAWIKI_API_URL, params)

    @classmethod
    def search(
        cls, query: str, language: str = "en", limit: int = 10, offset: int = 0
    ) -> list:
        """
        Search the data from the Wikimedia API.
        """
        response = cls.wbsearchentities(query, language, limit, offset)
        if response.status_code != status.HTTP_200_OK:
            raise WikibaseAPIException(response.status_code)
        content = response.json()
        return {
            "results": [
                {
                    "wikipedia_qid": item.get("id", ""),
                    "name": item.get("label", ""),
                    "description": item.get("description", ""),
                }
                for item in content.get("search", [])
            ],
            "search_continue": content.get("search-continue", None),
        }

    @classmethod
    def get_by_id(cls, wikipedia_qid: str) -> dict:
        """
        Get the data from the Wikimedia API.
        """
        response = cls.wbgetentities(wikipedia_qid)
        if response.status_code != status.HTTP_200_OK:
            raise WikibaseAPIException(response.status_code)
        content = response.json()["entities"][wikipedia_qid]
        names = {
            f"title_{language}": content["labels"][language]["value"]
            for language in settings.REQUIRED_LANGUAGES
            if language in content["labels"]
        }
        descriptions = {
            f"description_{language}": content["descriptions"][language]["value"]
            for language in settings.REQUIRED_LANGUAGES
            if language in content["descriptions"]
        }
        return {
            "wikipedia_qid": wikipedia_qid,
            **names,
            **descriptions,
        }
