from asgiref.sync import sync_to_async

from apps.commons.pagination import PageInfoLimitOffsetPagination


def AlgoliaPagination(count: int = 0):  # noqa: N802
    class _AlgoliaPagination(PageInfoLimitOffsetPagination):
        def get_count(self, queryset):
            return count

        async def paginate_queryset(self, queryset, request, view=None):
            await sync_to_async(super().paginate_queryset)(queryset, request, view)
            return [o async for o in queryset.aiterator()]

    return _AlgoliaPagination
