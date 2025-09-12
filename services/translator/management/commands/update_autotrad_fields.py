from typing import TypeVar

from django.contrib.contenttypes.models import ContentType
from django.core.management import BaseCommand
from django.db import models
from django.db.models import QuerySet

from apps.commons.mixins import OrganizationRelated
from services.translator.mixins import HasAutoTranslatedFields
from services.translator.models import AutoTranslatedField

T = TypeVar("T", bound=HasAutoTranslatedFields)


class Command(BaseCommand):
    def create_autotranslated_fields(self, queryset: QuerySet[T]):
        """
        Create AutoTranslatedField entries for new fields marked for
        auto-translation in the model's `auto_translated_fields`.
        """
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
            update_conflicts=False,
            ignore_conflicts=True,
            unique_fields=["content_type", "object_id", "field_name"],
        )
        print(
            f"Updated AutoTranslatedField for {queryset.count()} {queryset.model.__name__} instances"
        )

    def delete_autotranslated_fields(self, queryset: QuerySet[T]):
        """
        Delete AutoTranslatedField entries for fields that are no longer
        marked for auto-translation in the model's `auto_translated_fields`.
        """
        model = queryset.model
        content_type = ContentType.objects.get_for_model(model)
        translated_fields = model.auto_translated_fields
        AutoTranslatedField.objects.filter(content_type=content_type).exclude(
            field_name__in=translated_fields
        ).delete()
        print(
            f"Deleted obsolete AutoTranslatedField for {queryset.count()} {queryset.model.__name__} instances"
        )

    def handle(self, *args, **options):
        translated_models = [
            model
            for model in HasAutoTranslatedFields.__subclasses__()
            if (
                issubclass(model, models.Model)
                and issubclass(model, OrganizationRelated)
            )
        ]
        translated_instances = [
            model.objects.filter(
                model.organization_query("auto_translate_content", True)
            )
            for model in translated_models
        ]
        for queryset in translated_instances:
            queryset = queryset.distinct()
            self.create_autotranslated_fields(queryset)
            self.delete_autotranslated_fields(queryset)
