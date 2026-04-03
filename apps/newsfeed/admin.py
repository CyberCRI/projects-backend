from typing import Any

from django.contrib import admin
from django.db.models import Count
from django.db.models.query import QuerySet
from django.http.request import HttpRequest
from django.utils.formats import localize

from apps.newsfeed.models import (
    Event,
    EventLocation,
    Instruction,
    News,
    Newsfeed,
    NewsLocation,
)


class DisplayGroupMixins:
    """adminmixins for linked groups count from models"""

    @admin.display(description="targered groups numbers", ordering="count_groups")
    def display_count_groups(self, instance):
        return instance.count_groups

    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        return (
            super().get_queryset(request).annotate(count_groups=Count("people_groups"))
        )


@admin.register(Newsfeed)
class NewsfeedAdmin(admin.ModelAdmin):
    list_display = ("pk", "type")
    list_filter = ("type",)


@admin.register(News)
class NewsAdmin(DisplayGroupMixins, admin.ModelAdmin):
    list_display = (
        "title",
        "publication_date",
        "organization__code",
        "visible_by_all",
        "display_count_groups",
    )
    list_filter = ("publication_date", "organization", "visible_by_all")
    search_fields = ("title", "content", "people_groups__name")

    class NewsLocationAdminInline(admin.StackedInline):
        model = NewsLocation

    inlines = (NewsLocationAdminInline,)

    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        return super().get_queryset(request).select_related("organization")


@admin.register(Event)
class EventAdmin(DisplayGroupMixins, admin.ModelAdmin):
    list_display = (
        "title",
        "display_date",
        "organization__code",
        "visible_by_all",
        "display_count_groups",
    )
    list_filter = ("start_date", "end_date", "organization", "visible_by_all")
    search_fields = ("title", "content", "people_groups__name")

    class EventAdminInline(admin.StackedInline):
        model = EventLocation

    inlines = (EventAdminInline,)

    @admin.display(ordering="-start_date")
    def display_date(self, instance: Event):

        if instance.start_date == instance.end_date:
            return localize(instance.start_date)

        return f"{localize(instance.start_date)} -> {localize(instance.end_date)}"

    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        return super().get_queryset(request).select_related("organization")


@admin.register(Instruction)
class InstructionAdmin(DisplayGroupMixins, admin.ModelAdmin):
    list_display = (
        "title",
        "organization__code",
        "visible_by_all",
        "display_count_groups",
        "owner",
    )
    list_filter = ("publication_date", "organization", "visible_by_all")
    search_fields = ("title", "content", "people_groups__name")

    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        return super().get_queryset(request).select_related("organization", "owner")
