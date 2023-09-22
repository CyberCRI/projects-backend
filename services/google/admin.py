from typing import Any

from django.contrib import admin
from django.db.models.query import QuerySet
from django.http.request import HttpRequest

from .models import GoogleSyncErrors, LPIGoogleAccount, LPIGoogleGroup
from .tasks import (
    create_google_group_task,
    create_google_user_taks,
    suspend_google_user_task,
    update_google_group_task,
    update_google_user_task,
)


class LPIGoogleAccountAdmin(admin.ModelAdmin):
    list_display = ("keycloak_id", "email", "given_name", "family_name")
    search_fields = ("keycloak_id", "people_id", "email", "given_name", "family_name")
    exclude = (
        "last_login",
        "permissions",
        "groups",
        "people_id",
        "language",
        "birthdate",
        "pronouns",
        "personal_description",
        "short_description",
        "professional_description",
        "location",
        "job",
        "profile_picture",
        "sdgs",
        "facebook",
        "mobile_phone",
        "linkedin",
        "medium",
        "website",
        "skype",
        "landline_phone",
        "twitter",
        "people_data",
        "type",
    )
    actions = []
    list_filter = tuple()

    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        return super().get_queryset(request).filter(groups__organizations__code="CRI")

    def get_actions(self, request):
        actions = super().get_actions(request)
        if "delete_selected" in actions:
            del actions["delete_selected"]
        return actions

    class Meta:
        verbose_name = "Google account"


class LPIGoogleGroupAdmin(admin.ModelAdmin):
    list_display = ("name", "email")
    search_fields = ("name", "email")
    exclude = (
        "people_id",
        "type",
        "organization",
        "header_image",
        "logo_image",
        "featured_projects",
        "groups",
        "publication_status",
        "people_data",
        "order",
        "parent",
        "sdgs",
        "description",
    )
    actions = []

    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        return super().get_queryset(request).filter(organization__code="CRI")

    def get_actions(self, request):
        actions = super().get_actions(request)
        if "delete_selected" in actions:
            del actions["delete_selected"]
        return actions

    class Meta:
        verbose_name = "Google group"


class GoogleSyncErrorsAdmin(admin.ModelAdmin):
    list_display = ("user", "on_task", "error", "created_at")
    search_fields = (
        "user__email",
        "user__keycloak_id",
        "user__given_name",
        "user__family_name",
        "error",
    )
    ordering = ("-created_at",)
    list_filter = ("on_task",)
    readonly_fields = ("user", "on_task", "error", "created_at")
    actions = ["retry_action"]

    def retry_action(self, request: HttpRequest, queryset: QuerySet[Any]):
        for error in queryset:
            match error.on_task:
                case GoogleSyncErrors.OnTaskChoices.CREATE_USER:
                    create_google_user_taks.delay(error.user.keycloak_id)
                case GoogleSyncErrors.OnTaskChoices.UPDATE_USER:
                    update_google_user_task.delay(
                        error.user.keycloak_id, **error.task_kwargs
                    )
                case GoogleSyncErrors.OnTaskChoices.SUSPEND_USER:
                    suspend_google_user_task.delay(error.user.keycloak_id)
                case GoogleSyncErrors.OnTaskChoices.CREATE_GROUP:
                    create_google_group_task.delay(error.people_group.id)
                case GoogleSyncErrors.OnTaskChoices.UPDATE_GROUP:
                    update_google_group_task.delay(error.people_group.id)

    class Meta:
        verbose_name = "Google sync error"


admin.site.register(LPIGoogleAccount, LPIGoogleAccountAdmin)
admin.site.register(LPIGoogleGroup, LPIGoogleGroupAdmin)
admin.site.register(GoogleSyncErrors, GoogleSyncErrorsAdmin)
