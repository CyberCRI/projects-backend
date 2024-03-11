from django.contrib import admin

from .models import IdentityProvider, KeycloakAccount


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


class IdentityProviderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "alias",
        "enabled",
    )
    search_fields = ("alias",)


admin.site.register(KeycloakAccount, KeycloalAccountAdmin)
admin.site.register(IdentityProvider, IdentityProviderAdmin)
