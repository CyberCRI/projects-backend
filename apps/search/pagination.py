from apps.commons.pagination import PageInfoLimitOffsetPagination


def FixedCountPagination(count: int = 0):  # noqa: N802
    class _FixedCountPagination(PageInfoLimitOffsetPagination):
        def get_count(self, queryset):
            return count

        def paginate_queryset(self, queryset, request, view=None):
            return super(_FixedCountPagination, self).paginate_queryset(
                queryset, request, view
            )

    return _FixedCountPagination
