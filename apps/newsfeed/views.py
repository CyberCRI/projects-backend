import uuid

from django.db.models import F, QuerySet
from django.shortcuts import redirect
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from apps.accounts.permissions import HasBasePermission
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

    def get_projects_queryset(self):
        return (
            self.request.user.get_project_related_queryset(
                queryset=Newsfeed.objects.filter(
                    type=Newsfeed.NewsfeedType.PROJECT,
                    project__deleted_at__isnull=True,
                    project__score__completeness__gt=5,
                    project__organizations__code=self.kwargs["organization_code"],
                )
            )
            .annotate(date=F("project__updated_at"))
            .order_by("-date")
            .distinct()
        )

    def get_announcements_queryset(self):
        return (
            self.request.user.get_project_related_queryset(
                queryset=Newsfeed.objects.filter(
                    type=Newsfeed.NewsfeedType.ANNOUNCEMENT,
                    announcement__project__deleted_at__isnull=True,
                    announcement__project__organizations__code=self.kwargs[
                        "organization_code"
                    ],
                ),
                project_related_field="announcement__project",
            )
            .annotate(date=F("announcement__updated_at"))
            .order_by("-date")
            .distinct()
        )

    def get_news_queryset(self):
        return (
            self.request.user.get_news_related_queryset(
                queryset=Newsfeed.objects.filter(
                    type=Newsfeed.NewsfeedType.NEWS,
                    news__organization__code=self.kwargs["organization_code"],
                    news__publication_date__lte=timezone.now(),
                )
            )
            .annotate(date=F("news__publication_date"))
            .order_by("-date")
            .distinct()
        )

    def get_annotated_queryset(
        self, queryset: QuerySet[Newsfeed]
    ) -> QuerySet[Newsfeed]:
        ids = [item.id for item in queryset]
        return queryset.annotate(ordering=ArrayPosition(ids, F("id")))

    def get_queryset(self):
        announcements = self.get_annotated_queryset(self.get_announcements_queryset())
        news = self.get_annotated_queryset(self.get_news_queryset())
        projects = self.get_annotated_queryset(self.get_projects_queryset())
        return (announcements | news | projects).order_by("ordering")


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
