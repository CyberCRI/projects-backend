from django.contrib import admin

from .models import Notification


class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "type",
        "project",
        "receiver",
        "sender",
        "is_viewed",
        "to_send",
    )
    list_filter = ("type", "is_viewed", "to_send")


admin.site.register(Notification, NotificationAdmin)
