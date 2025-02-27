from django.contrib import admin
from django.contrib.auth.models import Group, Permission
from django.db import transaction
from django.db.models import Q, QuerySet
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from import_export import fields, resources
from import_export.admin import ExportActionMixin

from apps.accounts.models import PeopleGroup, ProjectUser
from apps.accounts.utils import get_group_permissions
from apps.commons.admin import RoleBasedAccessAdmin
from apps.emailing.models import Email
from apps.organizations.models import Organization
from services.keycloak.interface import KeycloakService


class UserResource(resources.ModelResource):
    portals = fields.Field()

    class Meta:
        fields = [
            "id",
            "slug",
            "email",
            "given_name",
            "family_name",
            "job",
            "portals",
            "language",
            "location",
            "sdgs",
            "created_at",
            "last_login",
        ]
        model = ProjectUser

    def dehydrate_portals(self, user: ProjectUser):
        organizations = user.get_related_organizations()
        return ",".join([f"{o.code}" for o in organizations])


class UserAdmin(ExportActionMixin, RoleBasedAccessAdmin):
    resource_classes = [UserResource]

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
        "last_login",
        ("keycloak_account", admin.EmptyFieldListFilter),
    )

    def get_queryset_for_organizations(
        self, queryset: QuerySet, organizations: QuerySet[Organization]
    ) -> QuerySet:
        """
        Filter the queryset based on the organizations the user has admin access to.
        """
        return queryset.filter(groups__organizations__in=organizations).distinct()

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
        if not request.user.is_superuser:
            del actions["create_email_for_users"]
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
        if instance.projects.exists():
            return self.format_permissions_up_to_date(
                instance.projects.get().permissions_up_to_date
            )
        if instance.people_groups.exists():
            return self.format_permissions_up_to_date(
                instance.people_groups.get().permissions_up_to_date
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
