from typing import TypeVar

from django.contrib.contenttypes.models import ContentType
from django.core.management import BaseCommand
from django.db.models import QuerySet

from apps.announcements.models import Announcement
from apps.feedbacks.models import Comment, Review
from apps.files.models import AttachmentFile, AttachmentLink
from apps.organizations.models import Organization
from apps.projects.models import (
    BlogEntry,
    Goal,
    Location,
    ProjectMessage,
    ProjectTab,
    ProjectTabItem,
)
from apps.skills.models import MentoringMessage
from services.translator.mixins import HasAutoTranslatedFields
from services.translator.models import AutoTranslatedField

T = TypeVar("T", bound=HasAutoTranslatedFields)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "-c",
            "--code",
            type=str,
            help="Organization code",
        )

    def init_autotranslated_fields(self, queryset: QuerySet[T]):
        content_type = ContentType.objects.get_for_model(queryset.model)
        translated_fields = queryset.model.auto_translated_fields
        AutoTranslatedField.objects.bulk_create(
            [
                AutoTranslatedField(
                    content_type=content_type,
                    object_id=str(instance.pk),
                    field_name=field_name,
                    up_to_date=False,
                )
                for instance in queryset
                for field_name in translated_fields
            ],
            batch_size=1000,
            update_conflicts=True,
            unique_fields=["content_type", "object_id", "field_name"],
            update_fields=["up_to_date"],
        )
        print(f"Initialized {queryset.count()} {queryset.model.__name__} instances")

    def handle(self, *args, **options):
        code = options["code"]
        if code is None:
            raise ValueError("You need to set organization code using -c or --code")
        organizations = Organization.objects.filter(code=code)
        if not organizations.exists():
            raise ValueError("Organization not found")
        organization = organizations.get()
        organizations.update(auto_translate_content=True)

        translated_instances = [
            organizations,
            organization.people_groups.all(),
            organization.get_all_members(),
            organization.projects.all(),
            organization.news.all(),
            organization.events.all(),
            organization.invitation_set.all(),
            organization.access_requests.all(),
            organization.attachment_files.all(),
            organization.project_categories.all(),
            organization.tag_classifications.all(),
            MentoringMessage.objects.filter(mentoring__organization=organization),
            Announcement.objects.filter(project__organizations=organization),
            ProjectMessage.objects.filter(project__organizations=organization),
            ProjectTab.objects.filter(project__organizations=organization),
            ProjectTabItem.objects.filter(tab__project__organizations=organization),
            Comment.objects.filter(project__organizations=organization),
            Review.objects.filter(project__organizations=organization),
            AttachmentLink.objects.filter(project__organizations=organization),
            AttachmentFile.objects.filter(project__organizations=organization),
            BlogEntry.objects.filter(project__organizations=organization),
            Goal.objects.filter(project__organizations=organization),
            Location.objects.filter(project__organizations=organization),
        ]
        for queryset in translated_instances:
            self.init_autotranslated_fields(queryset)
