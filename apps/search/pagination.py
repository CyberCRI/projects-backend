from apps.commons.pagination import PageInfoLimitOffsetPagination


def AlgoliaPagination(count: int = 0):  # noqa : N802
    class _AlgoliaPagination(PageInfoLimitOffsetPagination):
        def get_count(self, queryset):
            return count

        def paginate_queryset(self, queryset, request, view=None):
            super(_AlgoliaPagination, self).paginate_queryset(queryset, request, view)
            return list(queryset)

    return _AlgoliaPagination
