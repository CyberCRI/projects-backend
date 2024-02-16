from typing import Optional

from django.contrib import admin
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models import Embedding, ProjectEmbedding, UserEmbedding


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


admin.site.register(UserEmbedding, UserEmbeddingAdmin)
admin.site.register(ProjectEmbedding, ProjectEmbeddingAdmin)
