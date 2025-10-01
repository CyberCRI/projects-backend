from django.contrib import admin
from django.db.models import QuerySet
from import_export.admin import ExportActionMixin  # type: ignore

from apps.commons.admin import RoleBasedAccessAdmin
from apps.organizations.models import Organization

from .exports import BlogEntryResource, ProjectResource
from .models import BlogEntry, Project


@admin.register(Project)
class ProjectAdmin(ExportActionMixin, RoleBasedAccessAdmin):
    resource_classes = [ProjectResource, BlogEntryResource]

    def get_queryset_for_organizations(
        self, queryset: QuerySet[Project], organizations: QuerySet[Organization]
    ) -> QuerySet[Project]:
        return queryset.filter(organizations__in=organizations).distinct()

    list_display = (
        "id",
        "title",
        "purpose",
    )
    readonly_fields = (
        "groups",
        "images",
    )
    search_fields = (
        "id",
        "title",
        "purpose",
    )
    filter_horizontal = ("tags",)
    list_filter = (
        ("organizations", admin.RelatedOnlyFieldListFilter),
        ("categories", admin.RelatedOnlyFieldListFilter),
        "updated_at",
        "created_at",
    )


@admin.register(BlogEntry)
class BlogEntryAdmin(ExportActionMixin, RoleBasedAccessAdmin):
    resource_classes = [BlogEntryResource]

    def get_queryset_for_organizations(
        self, queryset: QuerySet[BlogEntry], organizations: QuerySet[Organization]
    ) -> QuerySet[BlogEntry]:
        return queryset.filter(project__organizations__in=organizations).distinct()

    list_display = (
        "id",
        "title",
        "project",
        "created_at",
        "updated_at",
    )
    readonly_fields = ("created_at", "updated_at", "images")
    search_fields = ("id", "title", "content")
    list_filter = (
        ("project__organizations", admin.RelatedOnlyFieldListFilter),
        "created_at",
        "updated_at",
    )
