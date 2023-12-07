from django.contrib import admin

from .models import KeycloakAccount


class KeycloalAccountAdmin(admin.ModelAdmin):
    list_display = ("id", "keycloak_id", "username", "email", "first_name", "last_name")
    search_fields = ("keycloak_id", "username", "email", "first_name", "last_name")


admin.site.register(KeycloakAccount, KeycloalAccountAdmin)
