from django.db.models import Model
from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.viewsets import GenericViewSet

from apps.accounts.models import ProjectUser

from .db.abc import HasOwner


class IgnoreCall:
    def __call__(self):
        """Ignore call by viewset's `get_permissions()`.

        `permission_classes` usually takes classes and not instance. This
        method allows the instance to be called as a constructor by just
        returning itself.
        """
        return self


class ReadOnly(permissions.BasePermission):
    """Allows safe methods."""

    def has_permission(self, request: Request, view: GenericViewSet) -> bool:
        return request.method in permissions.SAFE_METHODS

    def has_object_permission(
        self, request: Request, view: GenericViewSet, obj: Model
    ) -> bool:
        return self.has_permission(request, view)


class CreateOnly(permissions.BasePermission):
    """Allows create method."""

    def has_permission(self, request: Request, view: GenericViewSet) -> bool:
        return view.action == "create"

    def has_object_permission(
        self, request: Request, view: GenericViewSet, obj: Model
    ) -> bool:
        return self.has_permission(request, view)


class IsAuthenticatedOrCreateOnly(permissions.BasePermission):
    """Allows authenticated users to create."""

    def has_permission(self, request: Request, view: GenericViewSet) -> bool:
        return view.action == "create" or (
            request.user and request.user.is_authenticated
        )

    def has_object_permission(
        self, request: Request, view: GenericViewSet, obj: Model
    ) -> bool:
        return self.has_permission(request, view)


class IsOwner(permissions.BasePermission):
    """Allows the creator of an object."""

    def has_permission(self, request: Request, view: GenericViewSet) -> bool:
        if view.action not in ["create", "list"]:
            return request.user.is_authenticated
        return False

    def has_object_permission(
        self, request: Request, view: GenericViewSet, obj: HasOwner
    ) -> bool:
        return request.user.is_authenticated and obj.is_owned_by(request.user)


class WillBeOwner(permissions.BasePermission):
    def has_permission(self, request: Request, view: GenericViewSet) -> bool:
        if view.action == "create":
            user_id = None
            if not user_id and "id" in view.kwargs:
                user_id = ProjectUser.get_main_id(view.kwargs["id"])
            if not user_id and "user_id" in view.kwargs:
                user_id = ProjectUser.get_main_id(view.kwargs["user_id"])
            if not user_id and "user" in request.data:
                user_id = ProjectUser.get_main_id(request.data["user"])
            if user_id:
                return request.user.id == user_id
        return False

    def has_object_permission(
        self, request: Request, view: GenericViewSet, obj
    ) -> bool:
        return self.has_permission(request, view)
