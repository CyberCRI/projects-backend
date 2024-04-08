import uuid

from django.db.models import BigIntegerField, F, QuerySet
from django.shortcuts import redirect
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
from apps.newsfeed.models import Instruction, Newsfeed, News
from apps.newsfeed.serializers import InstructionSerializer, NewsfeedSerializer, NewsSerializer
from apps.organizations.permissions import HasOrganizationPermission

from .models import Event, Instruction, News, Newsfeed
from .serializers import EventSerializer, InstructionSerializer, NewsfeedSerializer, NewsSerializer

class NewsViewSet(viewsets.ModelViewSet):
    """Main endpoints for news."""

    serializer_class = NewsSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["updated_at"]
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
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ["updated_at"]
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

    def get_serializer_class(self):
        return self.serializer_class

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

    announcement_pattern = {
        0: {"index": 1, "step": 1},
        1: {"index": 3, "step": 2},
        2: {"index": 4, "step": 0},
    }

    project_pattern = {
        0: {"index": 1, "step": 1},
        1: {"index": 1, "step": 2},
        2: {"index": 3, "step": 3},
        3: {"index": 1, "step": 4},
        4: {"index": 2, "step": 0},
    }

    def get_ordered_dict(self, id_list, index, pattern):
        projects_index = {}
        step = 0

        for id_item in id_list:
            projects_index[index] = id_item
            index += pattern[step]["index"]
            step = pattern[step]["step"]

        return projects_index

    def get_queryset(self):
        projects_ids = self.request.user.get_project_queryset()

        projects_queryset = (
            Newsfeed.objects.filter(project__in=projects_ids)
            .annotate(updated_at=F("project__updated_at"))
            .distinct()
            .order_by("-updated_at")
        )

        announcements_queryset = (
            Newsfeed.objects.filter(type=Newsfeed.NewsfeedType.ANNOUNCEMENT)
            .annotate(updated_at=F("announcement__updated_at"))
            .distinct()
            .order_by("-updated_at")
        )

        projects_ids_list = [item.id for item in projects_queryset]
        announcements_ids_list = [item.id for item in announcements_queryset]

        ordered_projects_dict = self.get_ordered_dict(
            projects_ids_list, index=0, pattern=self.project_pattern
        )
        ordered_announcements_dict = self.get_ordered_dict(
            announcements_ids_list, index=3, pattern=self.announcement_pattern
        )

        ordered_news_list = []
        x = 0
        total_len = len(projects_ids_list) + len(announcements_ids_list)
        appended_projects = 0
        appended_announcements = 0
        while x < total_len:
            if ordered_announcements_dict.get(x):
                ordered_news_list.append(ordered_announcements_dict[x])
                appended_announcements += 1
            elif ordered_projects_dict.get(x):
                ordered_news_list.append(ordered_projects_dict[x])
                appended_projects += 1
            else:
                if appended_projects < len(projects_ids_list):
                    ordered_news_list = (
                        ordered_news_list + projects_ids_list[appended_projects:]
                    )
                else:
                    ordered_news_list = (
                        ordered_news_list
                        + announcements_ids_list[appended_announcements:]
                    )
                break
            x += 1

        ordering = ArrayPosition(
            ordered_news_list, F("id"), base_field=BigIntegerField()
        )

        return (
            Newsfeed.objects.filter(id__in=ordered_news_list)
            .annotate(ordering=ordering)
            .order_by("ordering")
        )


class EventViewSet(viewsets.ModelViewSet):
    """Main endpoints for projects."""

    serializer_class = EventSerializer
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
