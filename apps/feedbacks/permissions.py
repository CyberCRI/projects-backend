from django.db.models import Model
from rest_framework import permissions
from rest_framework.request import Request
from rest_framework.viewsets import GenericViewSet

from apps.projects.models import Project


class IsReviewable(permissions.BasePermission):
    def has_permission(self, request: Request, view: GenericViewSet) -> bool:
        if view.action == "create":
            project = Project.objects.get(id=view.kwargs["project_id"])
            return project.life_status == Project.LifeStatus.TO_REVIEW
        return True

    def has_object_permission(
        self, request: Request, view: GenericViewSet, obj: Model
    ) -> bool:
        return self.has_permission(request, view)
