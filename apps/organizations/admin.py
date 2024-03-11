from django.contrib import admin

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
        "wikipedia_tags",
        "identity_providers",
    )


admin.site.register(Organization, OrganizationAdmin)
