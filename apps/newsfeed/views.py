from django.db.models import BigIntegerField, F
from rest_framework import viewsets
from rest_framework.response import Response

from apps.commons.permissions import ReadOnly
from apps.commons.utils import ArrayPosition
from apps.newsfeed import filters
from apps.newsfeed.models import Newsfeed
from apps.newsfeed.serializers import NewsfeedSerializer


class NewsfeedViewSet(viewsets.ModelViewSet):
    serializer_class = NewsfeedSerializer
    filterset_class = filters.NewsfeedFilter
    permission_classes = [ReadOnly]

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
            .annotate(updated=F("project__updated_at"))
            .distinct()
            .order_by("-updated")
        )

        announcements_queryset = (
            Newsfeed.objects.filter(type=Newsfeed.NewsfeedType.ANNOUNCEMENT)
            .annotate(updated=F("announcement__updated_at"))
            .distinct()
            .order_by("-updated")
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

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            newsfeed_serializer = NewsfeedSerializer(
                page, many=True, context={"request": request}
            )
            return self.get_paginated_response(newsfeed_serializer.data)

        newsfeed_serializer = NewsfeedSerializer(
            queryset, many=True, context={"request": request}
        )
        return Response(newsfeed_serializer.data)
