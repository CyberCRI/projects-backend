from django.core.management import BaseCommand

from apps.commons.utils import process_unlinked_images
from apps.feedbacks.models import Comment
from apps.organizations.models import Faq, Template
from apps.projects.models import BlogEntry, Project


class Command(BaseCommand):
    def handle(self, *args, **options):
        for instance in Project.objects.all():
            updated_at = instance.updated_at
            images = process_unlinked_images(instance, instance.description)
            instance.images.add(*images)
            Project.objects.filter(id=instance.id).update(updated_at=updated_at)
        for instance in BlogEntry.objects.all():
            updated_at = instance.updated_at
            images = process_unlinked_images(instance, instance.content)
            instance.images.add(*images)
            BlogEntry.objects.filter(id=instance.id).update(updated_at=updated_at)
        for instance in Template.objects.all():
            images1 = process_unlinked_images(
                instance, instance.description_placeholder
            )
            images2 = process_unlinked_images(instance, instance.blogentry_placeholder)
            instance.images.add(*(images1 + images2))
        for instance in Faq.objects.all():
            images = process_unlinked_images(instance, instance.content)
            instance.images.add(*images)
        for instance in Comment.objects.all():
            updated_at = instance.updated_at
            images = process_unlinked_images(instance, instance.content)
            instance.images.add(*images)
            Comment.objects.filter(id=instance.id).update(updated_at=updated_at)
