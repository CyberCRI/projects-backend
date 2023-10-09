from typing import Any

from django.contrib import admin
from django.db.models.query import QuerySet
from django.http.request import HttpRequest

from .models import GoogleSyncErrors
from .tasks import (
    create_google_group_task,
    create_google_user_task,
    suspend_google_user_task,
    update_google_group_task,
    update_google_user_task,
)


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
                    create_google_user_task.delay(error.user.keycloak_id)
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


admin.site.register(GoogleSyncErrors, GoogleSyncErrorsAdmin)
