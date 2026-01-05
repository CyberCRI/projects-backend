import os

from django.contrib import admin
from django.db.models import QuerySet
from django.views import View
from guardian.shortcuts import get_objects_for_user

from apps.accounts.models import ProjectUser
from apps.organizations.models import Organization


class RoleBasedAccessAdmin(admin.ModelAdmin):
    """
    Admin class that restricts access to objects based on the user's role.
    This class is meant to be used as a mixin with Django's admin.ModelAdmin class.
    It must come before Django's admin.ModelAdmin class in the inheritance order :

    Example :
    class MyAdmin(RoleBasedAccessAdmin, admin.ModelAdmin):
        ...

    And not :
    class MyAdmin(admin.ModelAdmin, RoleBasedAccessAdmin):
        ...

    The class provides the following features:
        - Filter objects shown based on the user's role.
        - Restrict write access to superusers only.
        - Restrict read access to superusers only if `superadmin_only` is set to True.

    You must implement the `get_queryset_for_organizations` method in your subclass.
    """

    superadmin_only = False

    def _get_user_organizations(self, user: ProjectUser):
        """
        Get the organizations for which the user can access the admin panel.
        """
        return get_objects_for_user(user, "organizations.access_admin", Organization)

    def get_queryset(self, request) -> QuerySet:
        """
        Get the objects that the user has admin access to.
        """
        queryset = super().get_queryset(request)
        if request.user.is_superuser:
            return queryset
        return self.get_queryset_for_organizations(
            queryset, self._get_user_organizations(request.user)
        )

    def get_queryset_for_organizations(
        self, queryset: QuerySet, organizations: QuerySet[Organization]
    ) -> QuerySet:
        """
        Filter the queryset based on the organizations the user has admin access to.
        """
        raise NotImplementedError

    def has_add_permission(self, request):
        """
        Restrict create access to superusers only.
        """
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        """
        Restrict update access to superusers only.
        """
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        """
        Restrict delete access to superusers only.
        """
        return request.user.is_superuser

    def has_view_permission(self, request, obj=...):
        """
        Restrict read access to superusers only if `superadmin_only` is set to True.
        """
        if self.superadmin_only:
            return request.user.is_superuser
        return True

    def has_module_permission(self, request):
        """
        Restrict module access to superusers only if `superadmin_only` is set to True.
        """
        if self.superadmin_only:
            return request.user.is_superuser
        return True


class ExtraAdminMixins:
    """Mixins to convert view to admin custom View"""

    admin_site = None
    admin_app = None

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx = ctx | self.admin_site.each_context(self.request)
        ctx |= self.admin_app or {}
        return ctx


class RouterExtraAdmin:
    """Router to add custom route to admin django (need to add ExtraAdminMixins to your views)"""

    def __init__(self, name: str, app_label: str | None = None):
        self.name = name
        self.app_label = app_label or name
        self._register: list[tuple[str, type[View], dict, dict]] = []

    def register(
        self,
        path: str,
        view: View,
        name=None,
        object_name=None,
        model=None,
        permissions=None,
        view_only=True,
        **kw,
    ):
        kw_models = {
            "name": name or path,
            "object_name": object_name or path,
            "model": model,
            "permissions": permissions,
            "view_only": view_only,
        }
        self._register.append((os.path.join(self.app_label, path), view, kw_models, kw))

    @property
    def views(self):
        yield from self._register

    @property
    def app(self):
        return {
            "name": self.name,
            "app_label": self.app_label,
            "app_url": f"/admin/{self.app_label}/",
            "has_module_perms": True,
            "models": [
                {**kw_models, "admin_url": f"/admin/{path}"}
                for path, _, kw_models, kw in self._register
            ],
        }
