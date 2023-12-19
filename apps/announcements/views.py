from django.conf import settings
from django.utils.decorators import method_decorator
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import AllowAny, IsAuthenticatedOrReadOnly
from rest_framework.response import Response

from apps.accounts.permissions import HasBasePermission, ReadOnly
from apps.commons.utils.cache import clear_cache_with_key, redis_cache_view
from apps.notifications.tasks import notify_new_announcement, notify_new_application
from apps.organizations.permissions import HasOrganizationPermission
from apps.projects.models import Project
from apps.projects.permissions import HasProjectPermission

from .filters import AnnouncementFilter
from .models import Announcement
from .serializers import AnnouncementSerializer, ApplyToAnnouncementSerializer


class AnnouncementViewSet(viewsets.ModelViewSet):
    serializer_class = AnnouncementSerializer
    filterset_class = AnnouncementFilter
    lookup_field = "id"
    lookup_value_regex = "[0-9]+"
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["updated_at"]
    ordering = ["updated_at"]
    queryset = Announcement.objects.filter(project__deleted_at__isnull=True)
    permission_classes = [
        IsAuthenticatedOrReadOnly,
        ReadOnly
        | HasBasePermission("change_project", "projects")
        | HasOrganizationPermission("change_project")
        | HasProjectPermission("change_project"),
    ]

    def get_queryset(self):
        qs = self.queryset
        if "project_id" in self.kwargs:

            # TODO : handle with MultipleIDViewsetMixin
            project = Project.objects.filter(slug=self.kwargs["project_id"])
            if project.exists():
                self.kwargs["project_id"] = project.get().id

            qs = qs.filter(project=self.kwargs["project_id"])
        return qs.select_related("project")

    def perform_create(self, serializer):
        announcement = serializer.save()
        notify_new_announcement.delay(announcement.pk, self.request.user.pk)

    @extend_schema(request=ApplyToAnnouncementSerializer)
    @action(detail=True, methods=["post"], permission_classes=[AllowAny])
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
        return super(AnnouncementViewSet, self).dispatch(request, *args, **kwargs)


class ReadAnnouncementViewSet(AnnouncementViewSet):
    http_method_names = ["get", "list"]

    @method_decorator(
        redis_cache_view(
            "announcements_list_cache", settings.CACHE_ANNOUNCEMENTS_LIST_TTL
        )
    )
    def list(self, request, *args, **kwargs):
        return super(ReadAnnouncementViewSet, self).list(request, *args, **kwargs)
