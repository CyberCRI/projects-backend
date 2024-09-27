from django.core.management import BaseCommand
from django.template.defaultfilters import pluralize

from apps.skills.models import Tag
from apps.skills.utils import update_wikipedia_data


class Command(BaseCommand):

    def handle(self, *args, **options):
        update_wikipedia_data()
