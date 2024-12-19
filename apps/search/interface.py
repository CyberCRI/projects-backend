from typing import List, Optional, Union

from opensearchpy import Search
from opensearchpy.helpers.response import Response


class OpenSearchService:
    """
    Service to interact with the OpenSearch API.
    """

    @classmethod
    def search(
        cls,
        indices: Union[List[str], str],
        query: str,
        highlight: Optional[List[str]] = None,
        highlight_size: int = 150,
        limit: int = 100,
        offset: int = 0,
        **kwargs,
    ) -> Response:
        """
        Search for a query in the OpenSearch indices.

        Args:
            - indices: The indices to search in
            - query: The query to search for
            - highlight: The fields for which to return highlights
                ex: ["title", "description"]
            - highlight_size: The size of the highlights if any
            - limit: The maximum number of results to return
            - offset: The offset to start the search from
            - **kwargs: filters to apply to the search
        """
        request = (
            Search(using="default", index=indices)
            .query("multi_match", query=query)
            .params(size=limit, from_=offset)
        )
        if kwargs:
            request = request.filter("terms", **kwargs)
        if highlight:
            request = request.highlight(*highlight, fragment_size=highlight_size)
        return request.execute()

    @classmethod
    def best_fields_search(
        cls,
        indices: List[str],
        fields: List[str],
        query: str,
        highlight: Optional[List[str]] = None,
        highlight_size: int = 150,
        limit: int = 100,
        offset: int = 0,
        **kwargs,
    ) -> Response:
        """
        Search for a query in the OpenSearch indices using best_fields strategy.

        Args:
            - indices: The indices to search in
            - fields: The fields to search in with their weight
                ex: ["title^3", "description^2"]
            - query: The query to search for
            - highlight: The fields for which to return highlights
                ex: ["title", "description"]
            - highlight_size: The size of the highlights if any
            - limit: The maximum number of results to return
            - offset: The offset to start the search from
            - **kwargs: filters to apply to the search
        """
        request = (
            Search(using="default", index=indices)
            .query("multi_match", type="best_fields", fields=fields, query=query)
            .params(size=limit, from_=offset)
        )
        if kwargs:
            request = request.filter("terms", **kwargs)
        if highlight:
            request = request.highlight(*highlight, fragment_size=highlight_size)
        return request.execute()
