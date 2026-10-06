from django.contrib import admin

from .models import Invitation


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "organization",
        "description",
        "people_group",
        "expire_at",
        "created_at",
    )
    list_filter = ("organization",)
    search_fields = ("description",)
