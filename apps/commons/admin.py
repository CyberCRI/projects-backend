from typing import Iterable
from guardian.shortcuts import get_objects_for_user
from django.contrib import admin
from apps.organizations.models import Organization
from apps.accounts.models import ProjectUser


class RoleBasedAccessAdmin(admin.ModelAdmin):
    superadmin_only = False
    
    def _get_user_organizations(self, user: ProjectUser):
        return get_objects_for_user(user, "organizations.access_admin")
    
    def get_queryset(self, request):
        if request.user.is_superuser:
            return super().get_queryset(request)
        return self.get_queryset_for_organizations(
            self._get_user_organizations(request.user)
        )
    
    def get_queryset_for_organizations(self, organizations: Iterable[Organization]):
        raise NotImplementedError

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
    
    def has_module_permission(self, request):
        if self.superadmin_only:
            return request.user.is_superuser
        return True