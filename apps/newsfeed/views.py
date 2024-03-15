from django.db.models import BigIntegerField, F
from django_filters.rest_framework import DjangoFilterBackend

from apps.commons.permissions import ReadOnly
from apps.commons.utils import ArrayPosition
from apps.commons.views import ListViewSet
from apps.newsfeed.models import Newsfeed
from apps.newsfeed.serializers import NewsfeedSerializer


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
