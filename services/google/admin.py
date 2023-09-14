from typing import Any

from django.contrib import admin
from django.db.models.query import QuerySet
from django.http.request import HttpRequest

from .models import LPIGoogleAccount, LPIGoogleGroup


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


admin.site.register(LPIGoogleAccount, LPIGoogleAccountAdmin)
admin.site.register(LPIGoogleGroup, LPIGoogleGroupAdmin)
