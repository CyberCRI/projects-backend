import csv

from django import forms
from django.contrib import admin
from django.contrib.auth.models import Group, Permission
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from apps.accounts.models import PeopleGroup, ProjectUser
from apps.accounts.tasks import batch_create_users
from apps.accounts.utils import get_group_permissions
from apps.emailing.models import Email
from services.keycloak.interface import KeycloakService


class UserCSVImportMixin:
    class CsvImportForm(forms.Form):
        file = forms.FileField()
        update_mode = forms.ChoiceField(
            choices=(
                ("hard", "Completely update the data and add m2m"),
                ("soft", "Add the data if the field is empty and add m2m"),
                ("no_update", "Do not update anything"),
            ),
            initial="no_update",
        )

    def get_csv_import_urls(self):
        return [
            path("import-users-with-csv/", self.import_with_csv),
            path("download-csv-template/", self.get_csv_template),
        ]

    def import_with_csv(self, request):
        if not request.user.is_superuser:
            return HttpResponse("Unauthorized", status=403)
        if request.method == "POST":
            mode = request.POST.get("update_mode", "no_update")
            file = request.FILES["file"]
            file_data = file.read().decode("utf-8").splitlines()
            users_data = [user for user in csv.DictReader(file_data)]
            batch_create_users.delay(users_data, request.user.pk, mode)
            self.message_user(
                request,
                "Your csv file has been imported, a log file will be sent to you by email.",
            )
            return redirect("..")
        return render(
            request, "admin/upload_csv_form.html", {"form": self.CsvImportForm()}
        )

    def get_csv_template(self, request):
        if not request.user.is_superuser:
            return HttpResponse("Unauthorized", status=403)
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            'attachment; filename="user_import_fields.csv"'
        )
        writer = csv.writer(response)
        rows = [
            ["name", "example", "required"],
            ["email", "foo.bar@email.com", True],
            ["given_name", "Foo", True],
            ["family_name", "Bar", True],
            ["job", "Developer", True],
            ["external_id", "abcd1234", False],
            ["roles_to_add", "peoplegroup:#1:members;organization:#1:users", True],
            ["personal_email", "foo.bar@email.com", False],
            ["location", "Paris, France", False],
            ["birthdate", "YYYY-MM-DD", False],
            ["language", "en", False],
            ["pronouns", "she/her", False],
            ["personal_description", "<p>I am a developer</p>", False],
            ["short_description", "I am a developer", False],
            ["professional_description", "<p>I am a developer</p>", False],
            ["sdgs", "1;2;3", False],
            ["facebook", "https://www.facebook.com/foo.bar", False],
            ["mobile_phone", "+33612345678", False],
            ["linkedin", "https://www.linkedin.com/in/foo.bar", False],
            ["medium", "https://medium.com/@foo_bar", False],
            ["website", "https://www.foo.bar", False],
            ["skype", "foo.bar", False],
            ["landline_phone", "+33123456789", False],
            ["twitter", "https://twitter.com/foo_bar", False],
            ["redirect_organization_code", "CRI", False],
        ]
        writer.writerows(rows)
        return response


class UserAdmin(admin.ModelAdmin, UserCSVImportMixin):
    change_list_template = "admin/users_changelist.html"
    list_display = (
        "id",
        "keycloak_account_link",
        "email",
        "given_name",
        "family_name",
        "last_login",
    )

    search_fields = ("email", "given_name", "family_name")
    exclude = ("user_permissions",)
    filter_horizontal = ("groups",)
    actions = ["create_email_for_users"]
    list_filter = (
        "type",
        "last_login",
        ("keycloak_account", admin.EmptyFieldListFilter),
    )

    def keycloak_account_link(self, obj):
        if hasattr(obj, "keycloak_account"):
            admin_page = reverse(
                "admin:keycloak_keycloakaccount_change", args=(obj.keycloak_account.pk,)
            )
            return mark_safe(
                f'<a href="{admin_page}">{obj.keycloak_account}</a>'
            )  # nosec
        return None

    keycloak_account_link.short_description = "Keycloak account"

    def get_actions(self, request):
        actions = super().get_actions(request)
        if "delete_selected" in actions:
            del actions["delete_selected"]
        return actions

    def create_email_for_users(self, request, queryset):
        Email.objects.create(recipients=queryset)

    @transaction.atomic
    def save_model(self, request, obj, form, change) -> None:
        super().save_model(request, obj, form, change)
        if hasattr(obj, "keycloak_account"):
            KeycloakService.update_user(obj.keycloak_account)

    @transaction.atomic
    def delete_model(self, request, obj) -> None:
        if hasattr(obj, "keycloak_account"):
            KeycloakService.delete_user(obj.keycloak_account)
        return super().delete_model(request, obj)

    def get_urls(self):
        return [*self.get_csv_import_urls(), *super().get_urls()]

    class Meta:
        verbose_name = "User"


class GroupAdmin(admin.ModelAdmin):
    class GroupUsersInline(admin.TabularInline):
        model = Group.users.through

    class PermissionsUpToDateFilter(admin.SimpleListFilter):
        title = "permissions_up_to_date"
        parameter_name = "permissions_up_to_date"

        def lookups(self, request, model_admin):
            return (("True", True), ("False", False), ("None", None))

        def queryset(self, request, queryset):
            value = self.value()
            if value == "True":
                return queryset.filter(
                    Q(people_groups__permissions_up_to_date=True)
                    | Q(projects__permissions_up_to_date=True)
                    | Q(organizations__permissions_up_to_date=True)
                )
            if value == "False":
                return queryset.filter(
                    Q(people_groups__permissions_up_to_date=False)
                    | Q(projects__permissions_up_to_date=False)
                    | Q(organizations__permissions_up_to_date=False)
                )
            if value == "None":
                return queryset.filter(
                    Q(people_groups__isnull=True)
                    & Q(projects__isnull=True)
                    & Q(organizations__isnull=True)
                )
            return queryset

    list_display = ("name", "permissions_up_to_date")
    readonly_fields = ("permissions_representations",)
    exclude = ("permissions",)
    inlines = (GroupUsersInline,)
    search_fields = ("name",)
    list_filter = (PermissionsUpToDateFilter,)

    @staticmethod
    def format_permissions_up_to_date(permissions_up_to_date: bool) -> str:
        colors = {
            False: "#A00000",
            True: "#339933",
        }
        color = colors.get(permissions_up_to_date, "#686868")
        return format_html(f'<b style="color:{color};">{permissions_up_to_date}</b>')

    def permissions_up_to_date(self, instance: Group) -> str:
        if instance.people_groups.exists():
            return self.format_permissions_up_to_date(
                instance.people_groups.get().permissions_up_to_date
            )
        if instance.projects.exists():
            return self.format_permissions_up_to_date(
                instance.projects.get().permissions_up_to_date
            )
        if instance.organizations.exists():
            return self.format_permissions_up_to_date(
                instance.organizations.get().permissions_up_to_date
            )
        return self.format_permissions_up_to_date(None)

    def permissions_representations(self, instance: Group) -> str:
        return "- " + "\n- ".join(get_group_permissions(instance))


class PeopleGroupAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "organization", "email")
    search_fields = ("name", "email", "id")
    filter_horizontal = ("featured_projects",)
    list_filter = ("organization",)


class PermissionAdmin(admin.ModelAdmin):
    list_display = ("name", "codename", "content_type")
    search_fields = ("name", "codename", "content_type__model")


admin.site.unregister(Group)
admin.site.register(Group, GroupAdmin)
admin.site.register(PeopleGroup, PeopleGroupAdmin)
admin.site.register(ProjectUser, UserAdmin)
admin.site.register(Permission, PermissionAdmin)
