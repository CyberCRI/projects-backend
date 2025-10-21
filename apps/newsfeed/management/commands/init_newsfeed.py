from django.core.management import BaseCommand

from apps.newsfeed.utils import init_newsfeed


class Command(BaseCommand):
    def handle(self, *args, **options):
        init_newsfeed()
