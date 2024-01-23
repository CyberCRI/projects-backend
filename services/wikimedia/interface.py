import requests
import time

from mediawiki import MediaWiki
from django.conf import settings

class WikimediaService:
    MEDIAWIKI_API_URL = "https://www.wikidata.org/w/api.php"

    @classmethod
    def service(cls, language: str = "en") -> MediaWiki:
        """
        Get the Wikimedia service.
        """
        if not language in settings.REQUIRED_LANGUAGES:
            raise ValueError(f"Language {language} is not supported.")
        if not getattr(cls, f"service_{language}", None):
            setattr(cls, f"service_{language}", MediaWiki(lang=language))
        return getattr(cls, f"service_{language}")
    
    @classmethod
    def autocomplete(cls, query: str, language: str = "en", limit: int = 5) -> list:
        """
        Get the autocomplete data from the Wikimedia API.
        """
        response = cls.service(language).prefixsearch(query, results=limit)
        return response

    @classmethod
    def search(cls, query: str, language: str = "en", limit: int = 3, offset: int = 0) -> list:
        """
        Search the data from the Wikimedia API.
        """
        params = {
            "action": "wbsearchentities",
            "type": "item",
            "format": "json",
            "search": query,
            "language": language,
            "limit": limit,
            "continue": offset,
        }
        response = requests.get(cls.MEDIAWIKI_API_URL, params)
        content = response.json().get("search", [])
        return [
            {
                "id": item.get("id", ""),
                "label": item.get("label", ""),
                "description": item.get("description", ""),
            }
            for item in content
        ]
    
    @classmethod
    def get_by_id(cls, qid: str, default_language: str = "en") -> dict:
        """
        Get the data from the Wikimedia API.
        """
        params = {
            "action": "wbgetentities",
            "format": "json",
            "ids": qid
        }
        response = requests.get(cls.MEDIAWIKI_API_URL, params)
        content = response.json()['entities'][qid]['labels']
        data = {
            f"name_{language}": content[language]["value"]
            for language in settings.REQUIRED_LANGUAGES
            if language in content
        }
        data["name"] = ""
        return data
