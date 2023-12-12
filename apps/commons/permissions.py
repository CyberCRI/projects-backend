from django.db.models import Model
from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.viewsets import GenericViewSet

from .db.abc import HasOwner


class IgnoreCall:
    def __call__(self):
        """Ignore call by viewset's `get_permissions()`.

        `permission_classes` usually takes classes and not instance. This
        method allows the instance to be called as a constructor by just
        returning itself.
        """
        return self


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
            if "id" in view.kwargs:
                return str(request.user.id) == view.kwargs["id"]
            if "user_id" in view.kwargs:
                return str(request.user.id) == view.kwargs["user_id"]
            return str(request.user.id) == str(request.data.get("user"))
        return False

    def has_object_permission(
        self, request: Request, view: GenericViewSet, obj
    ) -> bool:
        return self.has_permission(request, view)


def IsAction(action: str):  # noqa : N802
    class _IsAction(permissions.BasePermission):
        def has_permission(self, request: Request, view: GenericViewSet) -> bool:
            return view.action == action

        def has_object_permission(
            self, request: Request, view: GenericViewSet, obj: Model
        ) -> bool:
            return self.has_permission(request, view)

    return _IsAction
