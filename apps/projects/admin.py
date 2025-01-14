from django.contrib import admin

from apps.commons.admin import RoleBasedAccessAdmin

from .models import Project


class ProjectAdmin(RoleBasedAccessAdmin):
    def get_queryset_for_organizations(self, organizations):
        return Project.objects.filter(organizations__in=organizations).distinct()

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


admin.site.register(Project, ProjectAdmin)
