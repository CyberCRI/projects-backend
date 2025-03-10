from django.contrib import admin
from django.db.models import QuerySet
from import_export import fields, resources # type: ignore
from import_export.admin import ExportActionMixin # type: ignore

from apps.commons.admin import RoleBasedAccessAdmin
from apps.organizations.models import Organization

from .models import Project


class ProjectResource(resources.ModelResource):
    members_names = fields.Field()
    members_emails = fields.Field()
    categories = fields.Field()
    tags = fields.Field()

    class Meta:
        fields = [
            "id",
            "slug",
            "title",
            "purpose",
            "description",
            "members_names",
            "members_emails",
            "publication_status",
            "life_status",
            "categories",
            "tags",
            "sdgs",
            "language",
            "is_locked",
            "updated_at",
            "created_at",
        ]
        model = Project

    def dehydrate_members_names(self, project: Project):
        return ",".join([f"{u.get_full_name()}" for u in project.get_all_members()])

    def dehydrate_members_emails(self, project: Project):
        return ",".join([f"{u.email}" for u in project.get_all_members()])

    def dehydrate_categories(self, project: Project):
        return ",".join([f"{c.name}" for c in project.categories.all()])

    def dehydrate_tags(self, project: Project):
        return ",".join([f"{t.title}" for t in project.tags.all()])


@admin.register(Project)
class ProjectAdmin(ExportActionMixin, RoleBasedAccessAdmin):
    resource_classes = [ProjectResource]

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
