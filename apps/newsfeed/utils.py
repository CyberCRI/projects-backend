from apps.announcements.models import Announcement
from apps.newsfeed.models import News, Newsfeed
from apps.projects.models import Project


def init_newsfeed():
    for project in Project.objects.all():
        Newsfeed.objects.get_or_create(
            project=project,
            defaults={
                "project": project,
                "type": Newsfeed.NewsfeedType.PROJECT,
            },
        )
    for announcement in Announcement.objects.all():
        Newsfeed.objects.get_or_create(
            announcement=announcement,
            defaults={
                "announcement": announcement,
                "type": Newsfeed.NewsfeedType.ANNOUNCEMENT,
            },
        )
    for news in News.objects.all():
        Newsfeed.objects.get_or_create(
            news=news,
            defaults={
                "news": news,
                "type": Newsfeed.NewsfeedType.NEWS,
            },
        )
