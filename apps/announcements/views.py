from django.utils.decorators import method_decorator
from django.views import View
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import AllowAny, IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from apps.accounts.permissions import HasBasePermission
from apps.commons.cache import clear_cache_with_key
from apps.commons.permissions import ReadOnly
from apps.commons.views import NestedProjectViewMixins
from apps.notifications.tasks import (
    notify_new_announcement,
    notify_new_application,
)
from apps.organizations.permissions import HasOrganizationPermission
from apps.projects.permissions import HasProjectPermission, ProjectIsNotLocked

from .filters import AnnouncementFilter
from .models import Announcement
from .serializers import AnnouncementSerializer, ApplyToAnnouncementSerializer


class AnnouncementViewSet(viewsets.ModelViewSet):
    serializer_class = AnnouncementSerializer
    filterset_class = AnnouncementFilter
    lookup_field = "id"
    lookup_value_regex = "[0-9]+"
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ("updated_at", "created_at", "deadline")
    ordering = ("updated_at",)
    # viewset only get/set lements
    http_method_names = ["get", "list"]

    def get_queryset(self):
        return self.request.user.get_project_related_queryset(
            Announcement.objects.filter(project__deleted_at__isnull=True)
        ).distinct()


class ProjectAnnouncementViewSet(NestedProjectViewMixins, viewsets.ModelViewSet):
    permission_classes = [
        IsAuthenticatedOrReadOnly,
        ProjectIsNotLocked,
        ReadOnly
        | HasBasePermission("change_project", "projects")
        | HasOrganizationPermission("change_project")
        | HasProjectPermission("change_project"),
    ]
    http_method_names = View.http_method_names

    def get_queryset(self):
        return self.project.modules_by_user(self.request.user).announcements()

    def perform_create(self, serializer):
        announcement = serializer.save()
        notify_new_announcement.delay(announcement.pk, self.request.user.pk)

    @extend_schema(request=ApplyToAnnouncementSerializer)
    @action(detail=True, methods=["POST"], permission_classes=[AllowAny])
    def apply(self, request, **kwargs):
        announcement = self.get_object()
        serializer = ApplyToAnnouncementSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        application = dict(serializer.validated_data)
        # Remove object that celery can't serializer since they can be retrieved with the announcement
        # related to announcement.pk
        del application["project"]
        del application["announcement"]
        notify_new_application.delay(announcement.pk, application)
        return Response(status=status.HTTP_200_OK)

    @method_decorator(clear_cache_with_key("announcements_list_cache"))
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)
