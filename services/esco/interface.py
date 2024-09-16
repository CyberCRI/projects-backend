import requests
from django.conf import settings


class EscoService:
    ESCO_API_URL = settings.ESCO_API_URL

    @classmethod
    def get_object_from_uri(
        cls, object_type: str, object_uri: str, language: str = "en"
    ):
        response = requests.get(
            f"{cls.ESCO_API_URL}/{object_type.lower()}/{object_uri}?language={language}"
        )
        response.raise_for_status()
        return response.json()

    @classmethod
    def get_all_objects(cls, language: str = "en", page_size: int = 100):
        data = []
        next_page = f"{cls.ESCO_API_URL}/search?language={language}&limit={page_size}"
        while next_page:
            response = requests.get(next_page)
            response.raise_for_status()
            content = response.json()
            results = content.get("_embedded", {}).get("results", [])
            results = [
                {
                    "type": result.get("className", ""),
                    "uri": result.get("_links", {}).get("self", {}).get("href", ""),
                }
                for result in results
                # Filter out results that have the "Taxonomy" type
                if result.get("className", "") in ["Occupation", "Skill", "Concept"]
            ]
            data.extend(results)
            next_page = content.get("_links", {}).get("next", {}).get("href", None)
        return data
