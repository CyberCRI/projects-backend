from typing import Optional

from django.conf import settings
from django.contrib import admin

from services.keycloak.interface import KeycloakService

from .exports import ProjectTemplateExportMixin
from .models import Organization, Template


@admin.register(Organization)
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
    )
    search_fields = (
        "code",
        "name",
        "website_url",
        "contact_email",
    )
    filter_horizontal = (
        "identity_providers",
        "featured_projects",
        "default_projects_tags",
        "default_skills_tags",
        "enabled_projects_tag_classifications",
        "enabled_skills_tag_classifications",
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


@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin, ProjectTemplateExportMixin):
    list_display = (
        "id",
        "get_organization",
        "project_category",
    )
    list_filter = ("project_category__organization",)
    actions = ["export_data"]

    def get_organization(self, template: Template) -> Optional[str]:
        if template.project_category and template.project_category.organization:
            return template.project_category.organization
        return None

    get_organization.short_description = "Organization"
