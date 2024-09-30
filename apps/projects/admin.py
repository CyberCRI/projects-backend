from django.contrib import admin

from .models import Project


class ProjectAdmin(admin.ModelAdmin):
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
