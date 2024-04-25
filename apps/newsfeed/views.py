import uuid

from django.db.models import BigIntegerField, F, QuerySet
from django.shortcuts import redirect
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from apps.accounts.permissions import HasBasePermission
from apps.announcements.models import Announcement
from apps.commons.permissions import ReadOnly
from apps.commons.utils import ArrayPosition, map_action_to_permission
from apps.commons.views import ListViewSet
from apps.files.models import Image
from apps.files.views import ImageStorageView
from apps.organizations.permissions import HasOrganizationPermission

from .filters import EventFilter, InstructionFilter, NewsFilter
from .models import Event, Instruction, News, Newsfeed
from .serializers import (
    EventSerializer,
    InstructionSerializer,
    NewsfeedSerializer,
    NewsSerializer,
)


class NewsViewSet(viewsets.ModelViewSet):
    """Main endpoints for news."""

    serializer_class = NewsSerializer
    filterset_class = NewsFilter
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["updated_at", "publication_date"]
    lookup_field = "id"
    lookup_value_regex = "[^/]+"

    def get_permissions(self):
        codename = map_action_to_permission(self.action, "news")
        if codename:
            self.permission_classes = [
                IsAuthenticatedOrReadOnly,
                ReadOnly
                | HasBasePermission(codename, "newsfeed")
                | HasOrganizationPermission(codename),
            ]
        return super().get_permissions()

    def get_queryset(self) -> QuerySet:
        if "organization_code" in self.kwargs:
            return self.request.user.get_news_queryset().filter(
                organization__code=self.kwargs["organization_code"]
            )
        return News.objects.none()

    def get_serializer_context(self):
        return {
            **super().get_serializer_context(),
            "organization_code": self.kwargs.get("organization_code", None),
        }

    def get_serializer(self, *args, **kwargs):
        """
        Force the usage of the organization code from the url in the serializer
        """
        if self.action in ["create", "update", "partial_update"]:
            self.request.data.update(
                {
                    "organization": self.kwargs["organization_code"],
                }
            )
        return super().get_serializer(*args, **kwargs)


class NewsHeaderView(ImageStorageView):
    permission_classes = [
        IsAuthenticatedOrReadOnly,
        ReadOnly
        | HasBasePermission("change_news", "newsfeed")
        | HasOrganizationPermission("change_news"),
    ]

    def get_queryset(self):
        if "news_id" in self.kwargs and "organization_code" in self.kwargs:
            return Image.objects.filter(
                news_header__organization__code=self.kwargs["organization_code"],
                news_header__id=self.kwargs["news_id"],
            )
        return Image.objects.none()

    @staticmethod
    def upload_to(instance, filename) -> str:
        return f"news/header/{uuid.uuid4()}#{instance.name}"

    def retrieve(self, request, *args, **kwargs):
        image = self.get_object()
        return redirect(image.file.url)

    def add_image_to_model(self, image):
        if "news_id" in self.kwargs and "organization_code" in self.kwargs:
            news = News.objects.get(
                id=self.kwargs["news_id"],
                organization__code=self.kwargs["organization_code"],
            )
            news.header_image = image
            news.save()
            return f"/v1/organization/{self.kwargs['organization_code']}/news/{self.kwargs['news_id']}/header/{image.id}"
        return None


class InstructionViewSet(viewsets.ModelViewSet):
    """Main endpoints for instructions."""

    serializer_class = InstructionSerializer
    filterset_class = InstructionFilter
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["updated_at", "publication_date"]
    lookup_field = "id"
    lookup_value_regex = "[^/]+"

    def get_permissions(self):
        codename = map_action_to_permission(self.action, "instruction")
        if codename:
            self.permission_classes = [
                IsAuthenticatedOrReadOnly,
                ReadOnly
                | HasBasePermission(codename, "newsfeed")
                | HasOrganizationPermission(codename),
            ]
        return super().get_permissions()

    def get_serializer(self, *args, **kwargs):
        """
        Force the usage of the organization code from the url in the serializer
        """
        if self.action in ["create", "update", "partial_update"]:
            self.request.data.update(
                {
                    "organization": self.kwargs["organization_code"],
                }
            )
        return super().get_serializer(*args, **kwargs)

    def get_queryset(self) -> QuerySet:
        if "organization_code" in self.kwargs:
            return self.request.user.get_instruction_queryset().filter(
                organization__code=self.kwargs["organization_code"]
            )
        return Instruction.objects.none()

    def get_serializer_context(self):
        return {
            **super().get_serializer_context(),
            "organization_code": self.kwargs.get("organization_code", None),
        }


class NewsfeedViewSet(ListViewSet):
    serializer_class = NewsfeedSerializer
    permission_classes = [ReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_class = None

    def get_queryset(self):
        projects_ids = (
            self.request.user.get_project_queryset()
            .filter(
                organizations__code=self.kwargs["organization_code"],
                score__completeness__gt=5,
            )
            .values_list("id", flat=True)
        )
        projects_queryset = (
            Newsfeed.objects.filter(project__in=projects_ids)
            .annotate(date=F("project__updated_at"))
            .distinct()
            .order_by("-date")
        )

        valid_announcements = Announcement.objects.filter(
            project__deleted_at__isnull=True
        )
        visible_announcements = valid_announcements.select_related("project")
        announcements_ids = visible_announcements.values_list("id", flat=True)
        announcements_queryset = (
            Newsfeed.objects.filter(announcement__in=announcements_ids)
            .annotate(date=F("announcement__updated_at"))
            .distinct()
            .order_by("-date")
        )

        visible_news = self.request.user.get_news_queryset().filter(
            organization__code=self.kwargs["organization_code"],
            publication_date__lte=timezone.now(),
        )
        news_ids = visible_news.values_list("id", flat=True)
        news_queryset = (
            Newsfeed.objects.filter(news__in=news_ids)
            .annotate(date=F("news__publication_date"))
            .distinct()
            .order_by("-date")
        )

        projects_ids_list = [item.id for item in projects_queryset]
        announcements_ids_list = [item.id for item in announcements_queryset]
        news_ids_list = [item.id for item in news_queryset]

        ordered_list = []
        x = 0
        greatest_len = max(
            len(projects_ids_list), len(announcements_ids_list), len(news_ids_list)
        )
        while x < greatest_len:
            if x < len(announcements_ids_list):
                ordered_list.append(announcements_ids_list[x])
            if x < len(news_ids_list):
                ordered_list.append(news_ids_list[x])
            if x < len(projects_ids_list):
                ordered_list.append(projects_ids_list[x])
            x += 1

        ordering = ArrayPosition(ordered_list, F("id"), base_field=BigIntegerField())

        return (
            Newsfeed.objects.filter(id__in=ordered_list)
            .annotate(ordering=ordering)
            .order_by("ordering")
        )


class EventViewSet(viewsets.ModelViewSet):
    """Main endpoints for projects."""

    serializer_class = EventSerializer
    filterset_class = EventFilter
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["event_date"]
    lookup_field = "id"
    lookup_value_regex = "[^/]+"

    def get_permissions(self):
        codename = map_action_to_permission(self.action, "event")
        if codename:
            self.permission_classes = [
                IsAuthenticatedOrReadOnly,
                ReadOnly
                | HasBasePermission(codename, "newsfeed")
                | HasOrganizationPermission(codename),
            ]
        return super().get_permissions()

    def get_queryset(self) -> QuerySet:
        if "organization_code" in self.kwargs:
            return self.request.user.get_event_queryset().filter(
                organization__code=self.kwargs["organization_code"]
            )
        return Event.objects.none()

    def get_serializer_context(self):
        return {
            **super().get_serializer_context(),
            "organization_code": self.kwargs.get("organization_code", None),
        }

    def get_serializer(self, *args, **kwargs):
        """
        Force the usage of the organization code from the url in the serializer
        """
        if self.action in ["create", "update", "partial_update"]:
            self.request.data.update(
                {
                    "organization": self.kwargs["organization_code"],
                }
            )
        return super().get_serializer(*args, **kwargs)
