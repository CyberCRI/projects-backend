from django.contrib import admin
from django.db.models import QuerySet
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
