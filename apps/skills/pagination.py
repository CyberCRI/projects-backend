from apps.commons.pagination import PageInfoLimitOffsetPagination


def WikipediaPagination(count: int):  # noqa: N802
    class _WikipediaPagination(PageInfoLimitOffsetPagination):
        def get_count(self, queryset):
            return count

        def paginate_queryset(self, queryset, request, view=None):
            super(_WikipediaPagination, self).paginate_queryset(queryset, request, view)
            return queryset

    return _WikipediaPagination
