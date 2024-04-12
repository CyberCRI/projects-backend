from typing import Any

from django.contrib import admin
from django.db.models.query import QuerySet
from django.http.request import HttpRequest

from .models import GoogleAccount, GoogleGroup, GoogleSyncErrors


class GoogleSyncErrorsAdmin(admin.ModelAdmin):
    list_display = (
        "google_account",
        "google_group",
        "on_task",
        "retries_count",
        "solved",
        "error",
        "created_at",
    )
    search_fields = (
        "google_account__email",
        "google_account__google_id",
        "google_account__user__email",
        "google_account__user__keycloak_account__keycloak_id",
        "google_account__user__given_name",
        "google_account__user__family_name",
        "google_group__email",
        "google_group__google_id",
        "google_group__people_group__name",
        "google_group__people_group__email",
        "error",
    )
    ordering = ("-created_at",)
    list_filter = (
        "on_task",
        "solved",
    )
    readonly_fields = (
        "on_task",
        "error",
        "created_at",
        "retries_count",
    )
    actions = ["retry", "mark_as_solved"]

    def retry(self, request: HttpRequest, queryset: QuerySet[Any]):
        for error in queryset:
            error.retry()

    def mark_as_solved(self, request: HttpRequest, queryset: QuerySet[Any]):
        queryset.update(solved=True)

    class Meta:
        verbose_name = "Google sync error"


class GoogleAccountAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "email",
        "organizational_unit",
        "google_id",
    )
    actions = [
        "create_in_google",
        "create_alias",
        "sync_data",
        "sync_groups",
        "sync_keycloak",
        "suspend",
    ]
    search_fields = (
        "user__given_name",
        "user__family_name",
        "user__email",
        "email",
    )
    list_filter = ("organizational_unit",)

    def create_in_google(self, request: HttpRequest, queryset: QuerySet[Any]):
        for account in queryset:
            account.create()

    def create_alias(self, request: HttpRequest, queryset: QuerySet[Any]):
        for account in queryset:
            account.create_alias()

    def sync_data(self, request: HttpRequest, queryset: QuerySet[Any]):
        for account in queryset:
            account.update()

    def sync_groups(self, request: HttpRequest, queryset: QuerySet[Any]):
        for account in queryset:
            account.sync_groups()

    def suspend(self, request: HttpRequest, queryset: QuerySet[Any]):
        for account in queryset:
            account.suspend()


class GoogleGroupAdmin(admin.ModelAdmin):
    list_display = (
        "people_group",
        "email",
        "google_id",
    )
    actions = ["create_in_google", "create_alias", "sync_data", "sync_members"]

    def create_in_google(self, request: HttpRequest, queryset: QuerySet[Any]):
        for group in queryset:
            group.create()

    def create_alias(self, request: HttpRequest, queryset: QuerySet[Any]):
        for group in queryset:
            group.create_alias()

    def sync_data(self, request: HttpRequest, queryset: QuerySet[Any]):
        for group in queryset:
            group.update()

    def sync_members(self, request: HttpRequest, queryset: QuerySet[Any]):
        for group in queryset:
            group.sync_members()


admin.site.register(GoogleSyncErrors, GoogleSyncErrorsAdmin)
admin.site.register(GoogleAccount, GoogleAccountAdmin)
admin.site.register(GoogleGroup, GoogleGroupAdmin)
