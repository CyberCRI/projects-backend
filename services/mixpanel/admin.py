from django.contrib import admin

from .models import MixpanelEvent


class MixpanelEventAdmin(admin.ModelAdmin):
    list_display = ("mixpanel_id", "date", "organization", "project")
    list_filter = ("date",)
    model = MixpanelEvent


admin.site.register(MixpanelEvent, MixpanelEventAdmin)
