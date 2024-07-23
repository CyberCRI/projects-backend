from django.db.models import Func, QuerySet
from django.db.models.constants import LOOKUP_SEP
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

    def construct_search(self, field_name, queryset):
        lookup = super().construct_search(field_name, queryset)
        lookup = lookup.split(LOOKUP_SEP)
        lookup.insert(len(lookup) - 1, "unaccent")
        return LOOKUP_SEP.join(lookup)
