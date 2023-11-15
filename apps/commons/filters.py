import unicodedata
from typing import List

from django.contrib.postgres.search import TrigramSimilarity
from django.db.models import F, Func, Q, QuerySet
from django_filters import filters


# Filter separating value by comma
class MultiValueCharFilter(filters.BaseCSVFilter, filters.CharFilter):
    def filter(self, query_set: QuerySet, value: str) -> QuerySet:  # noqa: A003
        # value is either a list or an 'empty' value
        if value:
            return super(MultiValueCharFilter, self).filter(query_set, value)
        return query_set


class UUIDFilter(filters.BaseCSVFilter, filters.UUIDFilter):
    def filter(self, query_set: QuerySet, value: str) -> QuerySet:  # noqa: A003
        # value is either a list or an 'empty' value
        if value:
            return super(UUIDFilter, self).filter(query_set, value)
        return query_set


class PostgresUnaccent(Func):
    function = "UNACCENT"


class TrigramSimilaritySearchFilter:
    @staticmethod
    def text_to_ascii(text):
        """Convert a text to ASCII."""
        text = unicodedata.normalize("NFD", text.lower())
        return str(text.encode("ascii", "ignore").decode("utf-8"))

    def trigram_search(
        self,
        queryset: QuerySet,
        query: str,
        fields: List[str],
        similarity_threshold: float = 0.3,
    ):
        trigram_search = Q()
        for field_name in fields:
            trigram_search |= Q(**{f"{field_name}__trigram_similar": query})

        return (
            queryset.objects.annotate(
                pg_similarity=sum(
                    [
                        TrigramSimilarity(
                            PostgresUnaccent(F(field)), self.text_to_ascii(query)
                        )
                        for field in fields
                    ]
                )
            )
            .filter(pg_similarity__gt=similarity_threshold)
            .order_by("-pg_similarity")
        )
