from typing import List

from django.db.models import Model
from rest_framework import permissions
from rest_framework.generics import get_object_or_404
from rest_framework.request import Request
from rest_framework.viewsets import GenericViewSet

from apps.accounts.models import PrivacySettings, ProjectUser
from apps.commons.mixins import OrganizationRelated, ProjectRelated
from apps.commons.permissions import IgnoreCall
from apps.commons.serializers import (
    OrganizationRelatedSerializer,
    ProjectRelatedSerializer,
)
from apps.files.models import Image
from apps.projects.models import Project

from .models import Organization


class OrganizationRelatedPermission(IgnoreCall):
    def get_related_organizations(
        self, request: Request, view: GenericViewSet, obj: Model = None
    ) -> List[Organization]:
        model = view.get_queryset().model
        if model == Organization:
            code = view.kwargs.get(view.lookup_url_kwarg) or view.kwargs.get(
                view.lookup_field
            )
            if code is not None:
                return Organization.objects.filter(code=code)
        if model == Project:
            pk = view.kwargs.get(view.lookup_url_kwarg) or view.kwargs.get(
                view.lookup_field
            )
            if pk is not None:
                return get_object_or_404(Project, pk=pk).get_related_organizations()
        if model in [ProjectUser, PrivacySettings]:
            user_id = view.kwargs.get(view.lookup_url_kwarg) or view.kwargs.get(
                view.lookup_field
            )
            if user_id is not None:
                obj = get_object_or_404(ProjectUser, id=user_id)
        if obj is None and "user_id" in view.kwargs and model == Image:
            obj = get_object_or_404(ProjectUser, id=view.kwargs["user_id"])
        if obj is None and "organization_code" in view.kwargs:
            return Organization.objects.filter(code=view.kwargs["organization_code"])
        if obj is None and "project_id" in view.kwargs:
            qs = Project.objects.filter(pk=view.kwargs["project_id"])
            if qs.exists():
                obj = qs.get()
        if obj is None and "category_id" in view.kwargs:
            return Organization.objects.filter(
                project_categories__id=view.kwargs["category_id"]
            )
        if obj is None and (view.lookup_url_kwarg or view.lookup_field) in view.kwargs:
            lookup_url_kwarg = view.lookup_url_kwarg or view.lookup_field
            filter_kwargs = {view.lookup_field: view.kwargs[lookup_url_kwarg]}
            obj = get_object_or_404(view.get_queryset(), **filter_kwargs)
        if obj is None and "organization" in view.request.data:
            return Organization.objects.filter(code=view.request.data["organization"])
        if obj is not None and isinstance(obj, OrganizationRelated):
            return obj.get_related_organizations()
        if obj is not None and isinstance(obj, ProjectRelated):
            return obj.get_related_project().get_related_organizations()

        serializer_class = view.get_serializer_class()
        if issubclass(serializer_class, OrganizationRelatedSerializer):
            serializer = serializer_class(
                data=request.data, context=view.get_serializer_context()
            )
            serializer.is_valid()
            return serializer.get_related_organizations()
        if issubclass(serializer_class, ProjectRelatedSerializer):
            serializer = serializer_class(
                data=request.data, context=view.get_serializer_context()
            )
            serializer.is_valid()
            return serializer.get_related_project().get_related_organizations()

        return []


def HasOrganizationPermission(  # noqa: N802
    codename: str, app: str = "organizations"
) -> permissions.BasePermission:
    class _HasOrganizationPermission(
        OrganizationRelatedPermission, permissions.BasePermission
    ):
        def has_permission(self, request: Request, view: GenericViewSet) -> bool:
            if request.user.is_authenticated:
                if app:
                    return any(
                        request.user.has_perm(f"{app}.{codename}", organization)
                        for organization in self.get_related_organizations(
                            request, view
                        )
                    )
                return any(
                    request.user.has_perm(codename, organization)
                    for organization in self.get_related_organizations(request, view)
                )
            return False

        def has_object_permission(
            self, request: Request, view: GenericViewSet, obj: Model
        ) -> bool:
            if request.user.is_authenticated:
                if app:
                    return any(
                        request.user.has_perm(f"{app}.{codename}", organization)
                        for organization in self.get_related_organizations(
                            request, view, obj
                        )
                    )
                return any(
                    request.user.has_perm(codename, organization)
                    for organization in self.get_related_organizations(
                        request, view, obj
                    )
                )
            return False

    return _HasOrganizationPermission
