from typing import List

from django.db.models import Model
from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.viewsets import GenericViewSet

from apps.accounts.models import PeopleGroup
from apps.commons.permissions import IgnoreCall


def HasBasePermission(  # noqa : N802
    codename: str, app: str = ""
) -> permissions.BasePermission:
    class _HasBasePermission(permissions.BasePermission):
        def has_permission(self, request: Request, view: GenericViewSet) -> bool:
            if request.user.is_authenticated:
                if app:
                    return request.user.has_perm(f"{app}.{codename}")
                return request.user.has_perm(codename)
            return False

        def has_object_permission(
            self, request: Request, view: GenericViewSet, obj: Model
        ) -> bool:
            return self.has_permission(request, view)

    return _HasBasePermission


class PeopleGroupRelatedPermission(IgnoreCall):
    def get_related_people_groups(
        self, view: GenericViewSet, obj: Model = None
    ) -> List[PeopleGroup]:
        if view.get_queryset().model == PeopleGroup:
            if obj is not None:
                return [obj]
            pk = view.kwargs.get(view.lookup_url_kwarg) or view.kwargs.get(
                view.lookup_field
            )
            if pk is not None:
                queryset = PeopleGroup.objects.filter(slug=pk)
                if queryset.exists():
                    return queryset
                return PeopleGroup.objects.filter(pk=pk)
        if "people_group_id" in view.kwargs:
            queryset = PeopleGroup.objects.filter(slug=view.kwargs["people_group_id"])
            if queryset.exists():
                return queryset
            return PeopleGroup.objects.filter(id=view.kwargs["people_group_id"])
        return []


def HasPeopleGroupPermission(  # noqa : N802
    codename: str, app: str = "accounts"
) -> permissions.BasePermission:
    class _HasPeopleGroupPermission(
        permissions.BasePermission, PeopleGroupRelatedPermission
    ):
        def has_permission(self, request: Request, view: GenericViewSet) -> bool:
            if request.user.is_authenticated:
                if app:
                    return any(
                        request.user.has_perm(f"{app}.{codename}", people_group)
                        for people_group in self.get_related_people_groups(view)
                    )
                return any(
                    request.user.has_perm(codename, people_group)
                    for people_group in self.get_related_people_groups(view)
                )
            return False

        def has_object_permission(
            self, request: Request, view: GenericViewSet, obj: Model
        ) -> bool:
            if request.user.is_authenticated:
                if app:
                    return any(
                        request.user.has_perm(f"{app}.{codename}", people_group)
                        for people_group in self.get_related_people_groups(view, obj)
                    )
                return any(
                    request.user.has_perm(codename, people_group)
                    for people_group in self.get_related_people_groups(view, obj)
                )
            return False

    return _HasPeopleGroupPermission
