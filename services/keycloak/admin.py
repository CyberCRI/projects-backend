from django.contrib import admin

from .models import KeycloakAccount


class KeycloalAccountAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "keycloak_id",
        "username",
        "email",
    )
    search_fields = (
        "keycloak_id",
        "username",
        "email",
    )


admin.site.register(KeycloakAccount, KeycloalAccountAdmin)
