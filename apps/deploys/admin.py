from django.contrib import admin
from django.utils.html import format_html

from .models import PostDeployProcess


class PostDeployProcessAdmin(admin.ModelAdmin):
    list_display = (
        "task_name",
        "priority",
        "last_run",
        "last_run_version",
        "status",
        "progress",
        "error",
    )
    readonly_fields = (
        "last_run",
        "last_run_version",
        "status",
        "progress",
        "traceback",
    )
    search_fields = (
        "id",
        "task_name",
    )
    exclude = ("_status", "_last_run")
    actions = ["run_task", "reset_task"]
    ordering = ("priority",)

    def run_task(self, request, queryset):
        for instance in queryset:
            instance.run_task()

    def reset_task(self, request, queryset):
        queryset.update(task_id="", last_run_version="")

    def status(self, instance):
        return self.format_status(instance.status)

    def error(self, instance):
        error = instance.error
        error = error.split("\n")
        last_2_lines = error[-5:-3]
        error = "\n".join(last_2_lines)
        return format_html(f"<pre>{error}</pre>")

    def traceback(self, instance):
        return format_html(f"<pre>{instance.error}</pre>")

    @staticmethod
    def format_status(status):
        status = status if status else PostDeployProcess.PostDeployProcessStatus.NONE
        color = {
            PostDeployProcess.PostDeployProcessStatus.SUCCESS: "#339933",
            PostDeployProcess.PostDeployProcessStatus.FAILURE: "#A00000",
        }.get(status, "#686868")
        return format_html(f'<b style="color:{color};">{status.capitalize()}</b>')


admin.site.register(PostDeployProcess, PostDeployProcessAdmin)
