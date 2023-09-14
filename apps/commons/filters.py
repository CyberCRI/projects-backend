from django.db.models import QuerySet
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
