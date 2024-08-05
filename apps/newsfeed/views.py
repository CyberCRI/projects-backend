import uuid
from itertools import chain, zip_longest

from django.db.models import F, Q, QuerySet
from django.shortcuts import redirect
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.settings import api_settings

from apps.accounts.permissions import HasBasePermission
from apps.commons.permissions import ReadOnly
from apps.commons.utils import map_action_to_permission
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
                    project__score__completeness__gte=5,
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
                project_related_name="announcement__project",
            )
            .filter(
                Q(announcement__deadline__gte=timezone.now())
                | Q(announcement__deadline__isnull=True)
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

    def merge_querysets(self, *querysets: QuerySet[Newsfeed]) -> QuerySet[Newsfeed]:
        """
        Merge the querysets into a single queryset using a round-robin strategy.
        The order of the querysets is preserved, as well as the order of the items in each queryset.

        Example:
        queryset_a = [a1, a2, a3]
        queryset_b = [b1, b2, b3, b4, b5]
        queryset_c = [c1, c2]

        merge_querysets(queryset_a, queryset_b, queryset_c) returns:
        [a1, b1, c1, a2, b2, c2, a3, b3, b4, b5]
        """
        merged = list(chain.from_iterable(zip_longest(*querysets, fillvalue=None)))
        return [item for item in merged if item is not None]

    def get_queryset(self):
        announcements = self.get_announcements_queryset()
        news = self.get_news_queryset()
        projects = self.get_projects_queryset()
        if announcements.exists():
            limit = self.request.query_params.get("limit", api_settings.PAGE_SIZE)
            first_page_announcements = announcements[: ((int(limit) + 2) // 3)]
            excluded_projects = first_page_announcements.values_list(
                "announcement__project__id", flat=True
            )
            projects = projects.exclude(project__id__in=excluded_projects)
        return self.merge_querysets(announcements, news, projects)


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


class NewsImagesView(ImageStorageView):
    permission_classes = [
        IsAuthenticatedOrReadOnly,
        ReadOnly
        | HasBasePermission("change_news", "newsfeed")
        | HasOrganizationPermission("change_news"),
    ]

    def get_queryset(self):
        if "news_id" in self.kwargs and "organization_code" in self.kwargs:
            return self.request.user.get_news_related_queryset(
                Image.objects.filter(
                    news__organization__code=self.kwargs["organization_code"],
                    news__id=self.kwargs["news_id"],
                )
            )
        return Image.objects.none()

    @staticmethod
    def upload_to(instance, filename) -> str:
        return f"news/images/{uuid.uuid4()}#{instance.name}"

    def retrieve(self, request, *args, **kwargs):
        image = self.get_object()
        return redirect(image.file.url)

    def add_image_to_model(self, image):
        if "news_id" in self.kwargs and "organization_code" in self.kwargs:
            news = News.objects.get(
                id=self.kwargs["news_id"],
                organization__code=self.kwargs["organization_code"],
            )
            news.images.add(image)
            news.save()
            return f"/v1/organization/{self.kwargs['organization_code']}/news/{self.kwargs['news_id']}/image/{image.id}"
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


class InstructionImagesView(ImageStorageView):
    permission_classes = [
        IsAuthenticatedOrReadOnly,
        ReadOnly
        | HasBasePermission("change_instruction", "newsfeed")
        | HasOrganizationPermission("change_instruction"),
    ]

    def get_queryset(self):
        if "instruction_id" in self.kwargs and "organization_code" in self.kwargs:
            return self.request.user.get_instruction_related_queryset(
                Image.objects.filter(
                    instructions__organization__code=self.kwargs["organization_code"],
                    instructions__id=self.kwargs["instruction_id"],
                ),
                instruction_related_name="instructions",
            )
        return Image.objects.none()

    @staticmethod
    def upload_to(instance, filename) -> str:
        return f"instructions/images/{uuid.uuid4()}#{instance.name}"

    def retrieve(self, request, *args, **kwargs):
        image = self.get_object()
        return redirect(image.file.url)

    def add_image_to_model(self, image):
        if "instruction_id" in self.kwargs and "organization_code" in self.kwargs:
            instruction = Instruction.objects.get(
                id=self.kwargs["instruction_id"],
                organization__code=self.kwargs["organization_code"],
            )
            instruction.images.add(image)
            instruction.save()
            return f"/v1/organization/{self.kwargs['organization_code']}/instruction/{self.kwargs['instruction_id']}/image/{image.id}"
        return None


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


class EventImagesView(ImageStorageView):
    permission_classes = [
        IsAuthenticatedOrReadOnly,
        ReadOnly
        | HasBasePermission("change_event", "newsfeed")
        | HasOrganizationPermission("change_event"),
    ]

    def get_queryset(self):
        if "event_id" in self.kwargs and "organization_code" in self.kwargs:
            return self.request.user.get_event_related_queryset(
                Image.objects.filter(
                    events__organization__code=self.kwargs["organization_code"],
                    events__id=self.kwargs["event_id"],
                ),
                event_related_name="events",
            )
        return Image.objects.none()

    @staticmethod
    def upload_to(instance, filename) -> str:
        return f"events/images/{uuid.uuid4()}#{instance.name}"

    def retrieve(self, request, *args, **kwargs):
        image = self.get_object()
        return redirect(image.file.url)

    def add_image_to_model(self, image):
        if "event_id" in self.kwargs and "organization_code" in self.kwargs:
            event = Event.objects.get(
                id=self.kwargs["event_id"],
                organization__code=self.kwargs["organization_code"],
            )
            event.images.add(image)
            event.save()
            return f"/v1/organization/{self.kwargs['organization_code']}/event/{self.kwargs['event_id']}/image/{image.id}"
        return None
