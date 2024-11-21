from django.core.management import BaseCommand

from apps.skills.utils import update_wikipedia_data


class Command(BaseCommand):

    def handle(self, *args, **options):
        update_wikipedia_data()
