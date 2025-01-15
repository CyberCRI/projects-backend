from apps.commons.pagination import PageInfoLimitOffsetPagination


def SearchPagination(count: int = 0):  # noqa: N802
    class _SearchPagination(PageInfoLimitOffsetPagination):
        def get_count(self, queryset):
            return count

        def paginate_queryset(self, queryset, request, view=None):
            """
            Queryset is already paginated by OpenSearchService.
            We need to set the count, offset and limit manually.
            """
            self.request = request
            self.count = self.get_count(queryset)
            self.offset = self.get_offset(request)
            self.limit = self.get_limit(request)
            return queryset

    return _SearchPagination
