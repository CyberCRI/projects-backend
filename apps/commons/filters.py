import unicodedata

from django.conf import settings
from django.contrib.postgres.search import TrigramSimilarity
from django.db.models import F, Func, QuerySet
from django_filters import filters
from rest_framework.filters import SearchFilter

from apps.accounts.models import ProjectUser


# Filter separating value by comma
class MultiValueCharFilter(filters.BaseCSVFilter, filters.CharFilter):
    def filter(self, query_set: QuerySet, value: str) -> QuerySet:  # noqa: A003
        # value is either a list or an 'empty' value
        if value:
            return super(MultiValueCharFilter, self).filter(query_set, value)
        return query_set


class UserMultipleIDFilter(MultiValueCharFilter):
    def __init__(self, user_id_field: str = "id", *args, **kwargs):
        self.user_id_field = user_id_field
        super().__init__(*args, **kwargs)

    def filter(self, queryset: QuerySet, value: str) -> QuerySet:  # noqa: A003
        if value:
            return super().filter(queryset, ProjectUser.get_main_ids(value))
        return queryset


class TrigramSearchFilter(SearchFilter):
    class PostgresUnaccent(Func):
        function = "UNACCENT"

    @staticmethod
    def text_to_ascii(text):
        """Convert a text to ASCII."""
        text = unicodedata.normalize("NFD", text.lower())
        return str(text.encode("ascii", "ignore").decode("utf-8"))

    def get_search_similarity_threshold(self, view):
        return getattr(
            view,
            "trigram_search_similarity_threshold",
            settings.PG_TRGM_DEFAULT_SIMILARITY_THRESHOLD,
        )

    def filter_queryset(self, request, queryset, view):
        search_fields = self.get_search_fields(view, request)
        search_terms = self.get_search_terms(request)
        if search_fields and search_terms:
            query = self.text_to_ascii(search_terms[0])
            return (
                queryset.annotate(
                    pg_similarity=sum(
                        [
                            TrigramSimilarity(
                                self.PostgresUnaccent(F(field)),
                                self.text_to_ascii(query),
                            )
                            for field in search_fields
                        ]
                    )
                )
                .filter(pg_similarity__gt=self.get_search_similarity_threshold(view))
                .order_by("-pg_similarity")
            )
        return queryset
