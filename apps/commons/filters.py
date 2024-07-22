import unicodedata

from django.db.models import Func, Q, QuerySet
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


class UnaccentSearchFilter(SearchFilter):
    class PostgresUnaccent(Func):
        function = "UNACCENT"

    @staticmethod
    def text_to_ascii(text):
        """Convert a text to ASCII."""
        text = unicodedata.normalize("NFD", text.lower())
        return str(text.encode("ascii", "ignore").decode("utf-8"))

    def filter_queryset(self, request, queryset, view):
        search_fields = self.get_search_fields(view, request)
        search_terms = self.get_search_terms(request)
        if search_fields and search_terms:
            search_term = self.text_to_ascii(search_terms[0])
            query = Q()
            for field in search_fields:
                query |= Q(**{f"{field}__unaccent__icontains": search_term})
            return queryset.filter(query)
        return queryset
