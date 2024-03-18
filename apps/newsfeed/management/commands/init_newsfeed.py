from django.core.management import BaseCommand

from apps.announcements.models import Announcement
from apps.newsfeed.models import Newsfeed
from apps.projects.models import Project


class Command(BaseCommand):
    def handle(self, *args, **options):
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
