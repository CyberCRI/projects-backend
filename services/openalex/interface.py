import requests
from rest_framework import status

from services.openalex.exceptions import OpenAlexAPIException


class OpenAlexService:
    API_URL = "https://api.openalex.org"

    ENTITY_TYPES = {
        "works",
        "authors",
        "institutions",
        "sources",
        "topics",
    }

    @classmethod
    def _get(
        cls,
        endpoint: str,
        params: dict | None = None,
    ) -> dict:
        """Make a request to the OpenAlex API."""
        response = requests.get(
            f"{cls.API_URL}/{endpoint}",
            params=params,
            headers={
                "Accept": "application/json",
            },
            timeout=30,
        )

        if response.status_code != status.HTTP_200_OK:
            raise OpenAlexAPIException(response.status_code)

        return response.json()

    @classmethod
    def _validate_entity_type(cls, entity_type: str) -> None:
        if entity_type not in cls.ENTITY_TYPES:
            raise ValueError(
                f"Unsupported entity type: {entity_type}. "
                f"Expected one of {sorted(cls.ENTITY_TYPES)}."
            )

    @classmethod
    def _get_title(cls, entity: dict) -> str:
        """Return the display title of an OpenAlex entity."""
        return entity.get("title") or entity.get("display_name") or ""

    @classmethod
    def _get_description(cls, entity: dict) -> str:
        """
        Return a description when available.

        OpenAlex works store abstracts as inverted indexes.
        Other entity types generally do not expose a Wikidata-like
        multilingual description field.
        """
        abstract_index = entity.get("abstract_inverted_index")

        if not abstract_index:
            return ""

        words = [
            (position, word)
            for word, positions in abstract_index.items()
            for position in positions
        ]

        return " ".join(word for _, word in sorted(words, key=lambda item: item[0]))

    @classmethod
    def _format_entity(cls, entity: dict) -> dict[str, str]:
        title = cls._get_title(entity)
        description = cls._get_description(entity)

        return {
            "external_id": entity["id"].rstrip("/").split("/")[-1],
            "fallback_title": title,
            "fallback_description": description,
            "title_en": title,
            "description_en": description,
        }

    @classmethod
    def search(
        cls,
        query: str,
        entity_type: str = "works",
        limit: int = 10,
        offset: int = 0,
        **params,
    ) -> tuple[list[str | int], int | None]:
        """
        Search OpenAlex entities.

        Returns:
            A tuple containing the OpenAlex IDs and the next offset.
        """
        cls._validate_entity_type(entity_type)

        if limit < 1 or limit > 200:
            raise ValueError("limit must be between 1 and 200.")

        if offset < 0 or offset % limit != 0:
            raise ValueError("offset must be non-negative and a multiple of limit.")

        page = offset // limit + 1

        content = cls._get(
            entity_type,
            params={
                "search": query,
                "per-page": limit,
                "page": page,
            },
        )

        results = content.get("results", [])
        ids = [entity["id"].rstrip("/").split("/")[-1] for entity in results]

        meta = content.get("meta", {})
        total_count = meta.get("count", 0)
        next_offset = offset + len(ids)

        if next_offset >= total_count or not ids:
            next_offset = None

        return ids, next_offset

    @classmethod
    def get_by_ids(
        cls,
        openalex_ids: list[str | int],
        entity_type: str = "works",
    ) -> list[dict[str, str]]:
        """
        Retrieve and format multiple OpenAlex entities.
        """
        cls._validate_entity_type(entity_type)

        if not openalex_ids:
            return []

        if len(openalex_ids) > 50:
            raise ValueError("The maximum number of OpenAlex IDs is 50 per request.")

        # OpenAlex supports filtering multiple IDs using OR.
        # IDs may be provided as W123... or full OpenAlex URLs.
        normalized_ids = [
            str(value).rstrip("/").split("/")[-1] for value in openalex_ids
        ]

        content = cls._get(
            entity_type,
            params={
                "filter": ("ids.openalex:" + "|".join(normalized_ids)),
                "per-page": len(normalized_ids),
            },
        )

        entities_by_id = {
            entity["id"].rstrip("/").split("/")[-1]: entity
            for entity in content.get("results", [])
        }

        # Preserve the caller's order and omit missing IDs.
        return [
            cls._format_entity(entities_by_id[entity_id])
            for entity_id in normalized_ids
            if entity_id in entities_by_id
        ]

    @classmethod
    def get_by_id(
        cls,
        openalex_id: str,
        entity_type: str = "works",
    ) -> dict[str, str] | None:
        """
        Retrieve and format a single OpenAlex entity.
        """
        entities = cls.get_by_ids([openalex_id], entity_type)
        return entities[0] if entities else None
