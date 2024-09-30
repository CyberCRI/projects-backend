from django.conf import settings
from django.contrib import admin

from services.keycloak.interface import KeycloakService

from .models import Organization


class OrganizationAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "website_url",
        "contact_email",
    )
    readonly_fields = (
        "groups",
        "images",
        "faq",
    )
    search_fields = (
        "code",
        "name",
        "website_url",
        "contact_email",
    )
    filter_horizontal = (
        "tags",
        "identity_providers",
        "featured_projects",
    )

    def save_model(self, request, obj, form, change):
        if obj.website_url:
            client_id = KeycloakService.get_client_id(
                settings.KEYCLOAK_FRONTEND_CLIENT_ID
            )
            data = KeycloakService.get_client(client_id)
            redirect_uris = data.get("redirectUris", [])
            if obj.website_url not in redirect_uris:
                redirect_uris.append(f"{obj.website_url}/*")
                data["redirectUris"] = redirect_uris
                KeycloakService.update_client(client_id, data)
        super().save_model(request, obj, form, change)


admin.site.register(Organization, OrganizationAdmin)
