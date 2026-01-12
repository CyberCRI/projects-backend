from typing import Any

from django.conf import settings
from django.contrib import admin
from django.db.models import Count, QuerySet
from django.http.request import HttpRequest

from apps.commons.admin import RoleBasedAccessAdmin, TranslateObjectAdminMixin
from services.keycloak.interface import KeycloakService

from .exports import ProjectTemplateExportMixin
from .models import Organization, ProjectCategory, Template, TemplateCategories


@admin.register(Organization)
class OrganizationAdmin(TranslateObjectAdminMixin, admin.ModelAdmin):
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
class TemplateAdmin(
    TranslateObjectAdminMixin, ProjectTemplateExportMixin, RoleBasedAccessAdmin
):
    list_display = (
        "id",
        "display_organization",
        "display_templates",
    )
    list_filter = ("categories__organization",)
    actions = ["export_data"]

    class TemplateCategoriesInline(admin.StackedInline):
        model = TemplateCategories

    inlines = (TemplateCategoriesInline,)

    def get_queryset(self, request) -> QuerySet:
        return (
            super().get_queryset(request).prefetch_related("categories__organization")
        )

    @admin.display(description="categories associates", ordering="categories__name")
    def display_templates(self, instance: Template):
        names = [o.name for o in instance.categories.all()]
        return " / ".join(names)

    @admin.display(
        description="Organization", ordering="categories__organization__name"
    )
    def display_organization(self, instance: Template) -> str | None:
        names = [o.organization.name for o in instance.categories.all()]
        return " / ".join(set(names))

    def get_queryset_for_organizations(
        self, queryset: QuerySet[Template], organizations: QuerySet[Organization]
    ) -> QuerySet[Template]:
        """
        Filter the queryset based on the organizations the user has admin access to.
        """
        return queryset.filter(categories__organization__in=organizations).distinct()


@admin.register(ProjectCategory)
class ProjectCategoryAdmin(TranslateObjectAdminMixin, admin.ModelAdmin):
    list_display = ("name", "display_templates")
    list_filter = ("name",)

    def get_queryset(self, request: HttpRequest) -> QuerySet[Any]:
        return (
            super().get_queryset(request).annotate(count_templates=Count("templates"))
        )

    @admin.display(description="numbers templates", ordering="count_templates")
    def display_templates(self, instance: ProjectCategory):
        return instance.count_templates
