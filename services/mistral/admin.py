from typing import Optional

from django.contrib import admin
from django.urls import reverse
from django.utils.safestring import mark_safe

from apps.accounts.models import ProjectUser
from apps.projects.models import Project

from .models import Embedding, EmbeddingError, ProjectEmbedding, UserEmbedding


class EmbeddingAdmin(admin.ModelAdmin):
    item_admin_page: str = ""
    search_fields: Optional[tuple] = None

    list_display = (
        "id",
        "item_link",
        "is_visible",
        "last_update",
    )
    actions = ["vectorize"]
    list_filter = ("is_visible",)

    def vectorize(self, request, queryset):
        for embedding in queryset:
            embedding.vectorize()

    def display_item_link(self, item: Embedding) -> str:
        raise NotImplementedError()

    def item_link(self, obj):
        if hasattr(obj, "item") and self.item_admin_page:
            admin_page = reverse(self.item_admin_page, args=(obj.item.pk,))
            return mark_safe(
                f'<a href="{admin_page}">{self.display_item_link(obj.item)}</a>'
            )  # nosec
        if hasattr(obj, "item"):
            return self.display_item_link(obj.item)
        return None

    item_link.short_description = "related_item"


class UserEmbeddingAdmin(EmbeddingAdmin):
    item_admin_page = "admin:accounts_projectuser_change"
    search_fields = ("item__given_name", "item__family_name", "item__email", "summary")

    def display_item_link(self, item: Embedding) -> str:
        return item.email


class ProjectEmbeddingAdmin(EmbeddingAdmin):
    item_admin_page = "admin:projects_project_change"
    search_fields = ("item__title", "item__purpose", "summary")

    def display_item_link(self, item: Embedding) -> str:
        return item.title


class EmbeddingErrorAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "link_to_item",
        "error",
        "created_at",
    )
    list_filter = ("error",)

    def link_to_item(self, item: EmbeddingError) -> str:
        if item.item_type == Project.__name__:
            admin_page = reverse("admin:projects_project_change", args=(item.item_id,))
        elif item.item_type == ProjectUser.__name__:
            admin_page = reverse(
                "admin:accounts_projectuser_change", args=(item.item_id,)
            )
        else:
            return None
        return mark_safe(f'<a href="{admin_page}">{item.item_type}: {item.item_id}</a>')

    link_to_item.short_description = "Item"


admin.site.register(UserEmbedding, UserEmbeddingAdmin)
admin.site.register(ProjectEmbedding, ProjectEmbeddingAdmin)
admin.site.register(EmbeddingError, EmbeddingErrorAdmin)
