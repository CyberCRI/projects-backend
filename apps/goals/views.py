from django.db.models import QuerySet
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from apps.accounts.permissions import HasBasePermission
from apps.commons.views import MultipleIDViewsetMixin
from apps.accounts.permissions import HasBasePermission
from apps.commons.permissions import ReadOnly
from apps.organizations.permissions import HasOrganizationPermission
from apps.projects.models import Project
from apps.projects.permissions import HasProjectPermission

from .models import Goal
from .serializers import GoalSerializer


class GoalViewSet(MultipleIDViewsetMixin, viewsets.ModelViewSet):
    serializer_class = GoalSerializer
    filter_backends = [DjangoFilterBackend]
    lookup_field = "id"
    lookup_value_regex = "[0-9]+"
    permission_classes = [
        IsAuthenticatedOrReadOnly,
        ReadOnly
        | HasBasePermission("change_project", "projects")
        | HasOrganizationPermission("change_project")
        | HasProjectPermission("change_project"),
    ]
    multiple_lookup_fields = [
        (Project, "project_id"),
    ]

    def get_queryset(self) -> QuerySet:
        if "project_id" in self.kwargs:
            qs = self.request.user.get_project_related_queryset(Goal.objects.all())
            return qs.filter(project=self.kwargs["project_id"])
        return Goal.objects.none()
