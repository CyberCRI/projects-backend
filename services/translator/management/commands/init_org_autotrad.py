from typing import TypeVar

from django.contrib.contenttypes.models import ContentType
from django.core.management import BaseCommand
from django.db import models
from django.db.models import QuerySet

from apps.commons.mixins import OrganizationRelated
from apps.organizations.models import Organization
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
        translated_fields = queryset.model._auto_translated_fields
        initial_count = AutoTranslatedField.objects.count()
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
        created = AutoTranslatedField.objects.count() - initial_count
        print(
            f"Initialized {created} AutoTranslatedField for {queryset.count()} {queryset.model.__name__} instances"
        )

    def handle(self, *args, **options):
        code = options["code"]
        if code is None:
            raise ValueError("You need to set organization code using -c or --code")
        organizations = Organization.objects.filter(code=code)
        if not organizations.exists():
            raise ValueError("Organization not found")
        organizations.update(auto_translate_content=True)
        translated_models = [
            model
            for model in HasAutoTranslatedFields.__subclasses__()
            if (
                issubclass(model, models.Model)
                and issubclass(model, OrganizationRelated)
            )
        ]
        translated_instances = [
            model.objects.filter(model.organization_query("code", code))
            for model in translated_models
        ]
        for queryset in translated_instances:
            self.init_autotranslated_fields(queryset.distinct())
