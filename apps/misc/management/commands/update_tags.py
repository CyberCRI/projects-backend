from django.core.management import BaseCommand
from django.template.defaultfilters import pluralize

from apps.misc import models
from services.wikipedia.interface import WikipediaService


class Command(BaseCommand):
    @staticmethod
    def is_unused(tag):
        for relation in models.WikipediaTag._meta.related_objects:
            model = relation.related_model
            field_name = relation.field.name
            queryset = model.objects.filter(**{field_name: tag})
            if queryset.count() > 0:
                return False
        return True

    def handle(self, *args, **options):
        deleted = 0
        updated = 0
        for tag in models.WikipediaTag.objects.all():
            if self.is_unused(tag):
                deleted += 1
                tag.delete()
            else:
                updated += 1
                WikipediaService.update_or_create_wikipedia_tag(tag.wikipedia_qid)
        self.stdout.write(
            self.style.SUCCESS(
                f"Process finished, {updated} tag{pluralize(updated)} updated "
                f"and {deleted} tag{pluralize(deleted)} deleted."
            )
        )
