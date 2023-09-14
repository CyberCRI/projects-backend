from django.contrib import admin

from .models import Email


class EmailAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "subject",
        "created_at",
        "has_been_sent_to_all",
    )
    search_fields = ("subject",)
    filter_horizontal = (
        "recipients",
        "sent_to",
        "images",
    )
    actions = (
        "send_to_recipients",
        "send_to_self",
    )

    @admin.action(description="Send to recipients")
    def send_to_recipients(self, request, queryset):
        for email in queryset:
            email.send()

    @admin.action(description="Send test to yourself")
    def send_to_self(self, request, queryset):
        for email in queryset:
            email.send_test(request.user)


admin.site.register(Email, EmailAdmin)
