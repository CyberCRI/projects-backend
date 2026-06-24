from collections.abc import Generator
from contextlib import suppress
from functools import cache
from typing import Any

from django.db.models import Model
from rest_framework import permissions
from rest_framework.generics import get_object_or_404
from rest_framework.request import Request
from rest_framework.viewsets import GenericViewSet

from apps.accounts.models import ProjectUser
from apps.commons.mixins import ProjectRelated
from apps.commons.permissions import IgnoreCall
from apps.commons.serializers import ProjectRelatedSerializer

from .exceptions import LockedProjectError
from .models import Project


class ProjectRelatedPermission(IgnoreCall):
    def __init__(self, *ar, **kw):
        super().__init__(*ar, **kw)

        # add locale cache
        self.get_related_project = cache(self.get_related_project)

    def get_related_project(
        self, request: Request, view: GenericViewSet, obj: Model | None = None
    ) -> Project | None:
        if view.get_queryset().model == Project:
            pk = view.kwargs.get(view.lookup_url_kwarg) or view.kwargs.get(
                view.lookup_field
            )
            if pk is not None:
                queryset = Project.objects.filter(slug=pk)
                with suppress(Project.DoesNotExist):
                    return queryset.get()
                return Project.objects.get(pk=pk)

        if obj is None and "project_id" in view.kwargs:
            queryset = Project.objects.filter(slug=view.kwargs["project_id"])
            with suppress(Project.DoesNotExist):
                return queryset.get()
            return Project.objects.get(pk=view.kwargs["project_id"])

        if obj is None and (view.lookup_url_kwarg or view.lookup_field) in view.kwargs:
            lookup_url_kwarg = view.lookup_url_kwarg or view.lookup_field
            filter_kwargs = {view.lookup_field: view.kwargs[lookup_url_kwarg]}
            obj = get_object_or_404(view.get_queryset(), **filter_kwargs)
        if obj is not None and isinstance(obj, ProjectRelated):
            return obj.get_related_project()
        serializer_class = view.get_serializer_class()
        if issubclass(serializer_class, ProjectRelatedSerializer):
            serializer = serializer_class(
                data=request.data, context=view.get_serializer_context()
            )
            serializer.is_valid()
            return serializer.get_related_project()
        return None


def HasProjectPermission(  # noqa: N802
    codename: str, app: str = "projects"
) -> permissions.BasePermission:
    class _HasProjectPermission(permissions.BasePermission, ProjectRelatedPermission):
        def __init__(self, *ar, **kw):
            super().__init__(*ar, **kw)

            self.has_permission = cache(self.has_permission)

        def has_permission(
            self, request: Request, view: GenericViewSet, project: Model = None
        ) -> bool:
            if request.user.is_authenticated:
                # If get_related_project returns None with a non-null obj, it might be
                # because the object is not yet linked to a project. In that case, it is
                # relevant to retry the permission check with the project_id in the URL.
                if not project:
                    project = self.get_related_project(request, view)
                if project and app:
                    return request.user.has_perm(f"{app}.{codename}", project)
                if project:
                    return request.user.has_perm(codename, project)
            return False

        def has_object_permission(
            self, request: Request, view: GenericViewSet, obj: Model
        ) -> bool:
            return self.has_permission(request, view, obj)

    return _HasProjectPermission


class ProjectIsNotLocked(permissions.BasePermission, ProjectRelatedPermission):
    def __init__(self, *ar, **kw):
        super().__init__(*ar, **kw)

        self.cache_iter_perms = cache(self.user_can_modify_locked_project)

    def iter_perms(
        self, project: Project, user: ProjectUser
    ) -> Generator[tuple[bool], Any, Any]:
        yield user.has_perm("projects.change_locked_project"),
        yield user.has_perm("projects.change_locked_project", project),
        for o in project.get_related_organizations():
            yield user.has_perm("organizations.change_locked_project", o)

    def user_can_modify_locked_project(
        self, project: Project, user: ProjectUser
    ) -> bool:
        return any(self.iter_perms(project, user))

    def has_permission(self, request: Request, view: GenericViewSet) -> bool:
        return self.has_object_permission(request, view, None)

    def has_object_permission(
        self, request: Request, view: GenericViewSet, obj: ProjectRelated
    ) -> bool:
        project = self.get_related_project(request, view, obj)

        if (
            project
            and view.action
            in [
                "create",
                "update",
                "partial_update",
                "destroy",
                "add_member",
                "remove_member",
            ]
            and project.is_locked
            and not self.user_can_modify_locked_project(project, request.user)
        ):
            raise LockedProjectError
        return True
