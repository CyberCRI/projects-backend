from django.contrib import admin
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models import Skill, Tag, TagClassification


class TagAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "type",
        "organization",
        "external_id",
        "title",
        "description",
    )
    list_filter = (
        "type",
        "organization",
    )
    search_fields = (
        "title",
        "title_en",
        "title_fr",
        "description",
        "description_en",
        "description_fr",
        "external_id",
    )


class TagClassificationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "slug",
        "type",
        "organization",
        "is_public",
        "title",
        "description",
    )
    list_filter = (
        "type",
        "organization",
        "is_public",
    )
    search_fields = (
        "title",
        "description",
    )
    filter_horizontal = ("tags",)


class SkillAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user_link",
        "tag_link",
        "type",
        "can_mentor",
        "needs_mentor",
    )
    list_filter = (
        "type",
        "can_mentor",
        "needs_mentor",
    )
    search_fields = (
        "user__email",
        "user__given_name",
        "user__family_name",
        "tag__title",
        "tag__title_en",
        "tag__title_fr",
    )

    def tag_link(self, obj):
        admin_page = reverse("admin:skills_tag_change", args=(obj.tag.pk,))
        return mark_safe(f'<a href="{admin_page}">{obj.tag}</a>')  # nosec

    def user_link(self, obj):
        admin_page = reverse("admin:accounts_projectuser_change", args=(obj.user.pk,))
        return mark_safe(f'<a href="{admin_page}">{obj.user.email}</a>')  # nosec

    tag_link.short_description = "Tag"
    user_link.short_description = "User"


admin.site.register(Tag, TagAdmin)
admin.site.register(TagClassification, TagClassificationAdmin)
admin.site.register(Skill, SkillAdmin)
