from typing import List

from django.db.models import Model
from rest_framework import permissions
from rest_framework.generics import get_object_or_404
from rest_framework.request import Request
from rest_framework.viewsets import GenericViewSet

from apps.commons.db.abc import ProjectRelated
from apps.commons.permissions import IgnoreCall
from apps.commons.serializers import ProjectRelatedSerializer

from .models import Project


class ProjectRelatedPermission(IgnoreCall):
    def get_related_projects(
        self, request: Request, view: GenericViewSet, obj: Model = None
    ) -> List[Project]:
        if view.get_queryset().model == Project:
            pk = view.kwargs.get(view.lookup_url_kwarg) or view.kwargs.get(
                view.lookup_field
            )
            if pk is not None:
                return Project.objects.filter(pk=pk)
        if obj is None and "project_id" in view.kwargs:
            return Project.objects.filter(pk=view.kwargs["project_id"])
        if obj is None and (view.lookup_url_kwarg or view.lookup_field) in view.kwargs:
            lookup_url_kwarg = view.lookup_url_kwarg or view.lookup_field
            filter_kwargs = {view.lookup_field: view.kwargs[lookup_url_kwarg]}
            obj = get_object_or_404(view.get_queryset(), **filter_kwargs)
        if obj is not None and isinstance(obj, ProjectRelated):
            return obj.get_related_projects()
        serializer_class = view.get_serializer_class()
        if issubclass(serializer_class, ProjectRelatedSerializer):
            serializer = serializer_class(
                data=request.data, context=view.get_serializer_context()
            )
            serializer.is_valid()
            return serializer.get_related_projects()
        return []


def HasProjectPermission(  # noqa : N802
    codename: str, app: str = "projects"
) -> permissions.BasePermission:
    class _HasProjectPermission(permissions.BasePermission, ProjectRelatedPermission):
        def has_permission(self, request, view):
            if request.user.is_authenticated:
                if app:
                    return any(
                        request.user.has_perm(f"{app}.{codename}", project)
                        for project in self.get_related_projects(request, view)
                    )
                return any(
                    request.user.has_perm(codename, project)
                    for project in self.get_related_projects(request, view)
                )
            return False

        def has_object_permission(self, request, view, obj):
            if request.user.is_authenticated:
                if app:
                    return any(
                        request.user.has_perm(f"{app}.{codename}", project)
                        for project in self.get_related_projects(request, view, obj)
                    )
                return any(
                    request.user.has_perm(codename, project)
                    for project in self.get_related_projects(request, view, obj)
                )
            return False

    return _HasProjectPermission


class ProjectIsNotLocked(permissions.BasePermission):
    message = "This project is locked."

    def has_object_permission(
        self, request: Request, view: GenericViewSet, obj: Project
    ) -> bool:
        if view.action in ["update", "partial_update"]:
            return not obj.is_locked
        return True
