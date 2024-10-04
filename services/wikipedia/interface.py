from typing import Dict, List, Optional, Tuple

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
    def wbgetentities(cls, wikipedia_qids: List[str]) -> requests.Response:
        """
        Get the data for multiple Wikipedia Tags from the Wikimedia API.
        """
        params = {"action": "wbgetentities", "format": "json", "ids": wikipedia_qids}
        return requests.get(cls.MEDIAWIKI_API_URL, params)

    @classmethod
    def get_by_ids(cls, wikipedia_qids: List[str]) -> List[Dict[str, str]]:
        """
        Get and format the data for multiple Wikipedia Tags from the Wikimedia API.
        """
        response = cls.wbgetentities(wikipedia_qids)
        if response.status_code != status.HTTP_200_OK:
            raise WikibaseAPIException(response.status_code)
        content = response.json()["entities"]
        return [
            {
                "external_id": wikipedia_qid,
                **{
                    f"title_{language}": content[wikipedia_qid]["labels"][language][
                        "value"
                    ]
                    for language in settings.REQUIRED_LANGUAGES
                    if language in content[wikipedia_qid]["labels"]
                },
                **{
                    f"description_{language}": content[wikipedia_qid]["descriptions"][
                        language
                    ]["value"]
                    for language in settings.REQUIRED_LANGUAGES
                    if language in content[wikipedia_qid]["descriptions"]
                },
            }
            for wikipedia_qid in wikipedia_qids
        ]

    @classmethod
    def get_by_id(cls, wikipedia_qid: str) -> dict:
        """
        Get and format the data for a single Wikipedia Tag from the Wikimedia API.
        """
        entities = cls.get_by_ids([wikipedia_qid])
        return entities[0] if entities else None

    @classmethod
    def search(
        cls, query: str, language: str = "en", limit: int = 10, offset: int = 0
    ) -> Tuple[List[Dict[str, str]], Optional[int]]:
        """
        Search Tags and get formatted data from the Wikimedia API.
        """
        response = cls.wbsearchentities(query, language, limit, offset)
        if response.status_code != status.HTTP_200_OK:
            raise WikibaseAPIException(response.status_code)
        content = response.json()
        next_items = content.get("search-continue", None) or 0
        wikipedia_qids = [item.get("id", "") for item in content.get("search", [])]
        return wikipedia_qids, next_items
