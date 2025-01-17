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
        fuzziness: Union[int, str] = 1,
        prefix_length: int = 1,
        max_expansions: int = 10,
        fuzzy_transpositions: bool = True,
        **kwargs,
    ) -> Response:
        """
        Search for a query in the OpenSearch indices.

        Args:
            - indices: list[str]
                The indices to search in
            - query: str
                The query to search for
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
                query=query,
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
        fuzziness: Union[int, str] = 1,
        prefix_length: int = 1,
        max_expansions: int = 10,
        fuzzy_transpositions: bool = True,
        **kwargs,
    ) -> Response:
        """
        Search for a query in the OpenSearch indices using best_fields strategy.

        Args:
            - indices: list[str]
                The indices to search in
            - fields: list[str]
                The fields to search in with their weight
                ex: ["title^3", "description^2"]
            - query: str
                The query to search for
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
                type="best_fields",
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

    @classmethod
    def wildcard_search(
        cls,
        indices: List[str],
        fields: List[str],
        query: str,
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
        Search for a query in the OpenSearch indices using wildcard and best fields
        strategies

        Args:
            - indices: list[str]
                The indices to search in
            - fields: list[str]
                The fields to search in with their weight
                ex: ["title^3", "description^2"]
            - query: str
                The query to search for
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
        wildcard_query = {
            "bool": {
                "should": [
                    {
                        "wildcard": {
                            field.split("^")[0]: {
                                "value": f"*{query}*",
                                "case_insensitive": True,
                                "boost": (
                                    float(field.split("^")[1]) if "^" in field else 1.0
                                ),
                            }
                        },
                    }
                    for field in fields
                ]
                + [
                    {
                        "fuzzy": {
                            field.split("^")[0]: {
                                "value": query,
                                "fuzziness": fuzziness,
                                "prefix_length": prefix_length,
                                "max_expansions": max_expansions,
                                "transpositions": fuzzy_transpositions,
                                "boost": (
                                    float(field.split("^")[1]) if "^" in field else 1.0
                                ),
                            }
                        }
                    }
                    for field in fields
                ]
            }
        }
        request = (
            Search(using="default", index=indices)
            .query(wildcard_query)
            .params(size=limit, from_=offset)
        )
        if kwargs:
            request = request.filter("terms", **kwargs)
        if highlight:
            request = request.highlight(*highlight, fragment_size=highlight_size)
        return request.execute()
