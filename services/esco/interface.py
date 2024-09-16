import requests
from django.conf import settings


class EscoService:
    ESCO_API_URL = settings.ESCO_API_URL

    @classmethod
    def get_object_from_uri(cls, object_type: str, object_uri: str):
        response = requests.get(
            f"{cls.ESCO_API_URL}/resource/{object_type}?uri={object_uri}"
        )
        response.raise_for_status()
        return response.json()

    @classmethod
    def get_all_objects(
        cls, object_type: str = "", language: str = "en", page_size: int = 100
    ):
        data = []
        next_page = (
            f"{cls.ESCO_API_URL}/search"
            f"?type={object_type}"
            f"&language={language}"
            f"&limit={page_size}"
        )
        while next_page:
            response = requests.get(next_page)
            response.raise_for_status()
            content = response.json()
            results = content.get("_embedded", {}).get("results", [])
            results = [
                {
                    "type": result.get("className", ""),
                    "uri": result.get("uri", ""),
                }
                for result in results
                # Filter out results that have the "Taxonomy" type
                if result.get("className", "") != "Taxonomy"
            ]
            data.extend(results)
            next_page = content.get("_links", {}).get("next", {}).get("href", None)
        return data
