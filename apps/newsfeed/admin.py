from django.contrib import admin
from django.db.models import Count
from django.db.models.query import QuerySet
from django.http.request import HttpRequest

from apps.newsfeed.models import News


@admin.register(News)
class NewsAdmin(admin.ModelAdmin):
    list_display = ("title", "organization", "get_group_count")
    list_display_links = (
        list_display[0],
        "organization",
    )
    list_filter = (
        "organization",
        "people_groups",
        "visible_by_all",
        "publication_date",
    )
    search_fields = ("title", "content")

    def get_queryset(self, request: HttpRequest) -> QuerySet[News]:
        return (
            super()
            .get_queryset(request)
            .select_related("organization")
            .prefetch_related("people_groups")
            .annotate(group_count=Count("people_groups"))
        )

    @admin.display(description="numbers of groups", ordering="-group_count")
    def get_group_count(self, instance: News) -> int:
        return instance.group_count
