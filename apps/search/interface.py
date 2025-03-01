from typing import List, Optional, Union

from opensearchpy import Search
from opensearchpy.helpers.response import Response


class OpenSearchService:
    """
    Service to interact with the OpenSearch API.
    """

    @classmethod
    def multi_match_search(
        cls,
        indices: List[str],
        fields: List[str],
        query: str,
        search_type: str = "most_fields",
        highlight: Optional[List[str]] = None,
        highlight_size: int = 150,
        limit: int = 100,
        offset: int = 0,
        fuzziness: Union[int, str] = 1,
        prefix_length: int = 1,
        max_expansions: int = 10,
        fuzzy_transpositions: bool = True,
        **kwargs,
    ) -> Response:
        """
        Search for a query in the OpenSearch indices using multi_match strategy.

        Args:
            - indices: list[str]
                The indices to search in
            - fields: list[str]
                The fields to search in with their weight
                ex: ["title^3", "description^2"]
            - query: str
                The query to search for
            - search_type: str = "most_fields"
                The type of multi_match search to perform
                ex: "best_fields", "most_fields"
            - highlight: list[str] | None = None
                The fields for which to return highlights
                ex: ["title", "description"]
            - highlight_size: int = 150
                The size of the highlights if any
            - limit: int = 100
                The maximum number of results to return
            - offset: int = 0
                The offset to start the search from
            - fuzziness: int | str = 1
                The level of tolerance for typos
                ex: "AUTO", 1, 2
            - prefix_length: int
                The number of initial characters which will not be "fuzzified"
            - max_expansions: int = 10
                The maximum number of variations if the search term
            - fuzzy_transpositions: bool = True
                Whether transpositions ("ab" -> "ba") are treated as a single edit
            - **kwargs
                filters to apply to the search

        Returns:
            opensearchpy.helpers.response.Response
        """
        request = (
            Search(using="default", index=indices)
            .query(
                "multi_match",
                type=search_type,
                query=query,
                fields=fields,
                fuzziness=fuzziness,
                prefix_length=prefix_length,
                max_expansions=max_expansions,
                fuzzy_transpositions=fuzzy_transpositions,
            )
            .params(size=limit, from_=offset)
        )
        if kwargs:
            request = request.filter("terms", **kwargs)
        if highlight:
            request = request.highlight(*highlight, fragment_size=highlight_size)
        return request.execute()
