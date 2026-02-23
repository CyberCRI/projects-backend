import logging

from django.contrib.contenttypes.models import ContentType

from apps.commons.utils import clear_memory
from projects.celery import app

from .models import AutoTranslatedField
from .utils import update_auto_translated_field

logger = logging.getLogger(__name__)


@app.task(name="apps.translations.tasks.automatic_translations")
@clear_memory
def automatic_translations():
    for field in AutoTranslatedField.objects.filter(up_to_date=False):
        try:
            update_auto_translated_field(field)
        except Exception as e:  # noqa: PIE786
            logger.error(f"Error updating auto-translated field {field.id}: {e}")


@app.task(name="apps.translations.tasks.translate_object")
@clear_memory
def translate_object(
    content_type_id: int, object_id: int, fields_name: list[str] | None = None
):
    """force retranslate all field from one models

    :param content_type_id: content_type model id
    :param object_id: model id
    """

    model = ContentType.objects.get(id=content_type_id)
    queryset = AutoTranslatedField.objects.filter(
        content_type=model, object_id=object_id
    )
    if fields_name is not None:
        queryset = queryset.filter(field_name__in=fields_name)

    logger.info(
        "Start translated model %r(id=%s) for fields %r",
        model,
        object_id,
        fields_name if fields_name is not None else "all",
    )

    for field in queryset:
        try:
            update_auto_translated_field(field)
        except Exception as e:  # noqa: PIE786
            logger.error(
                f"Error updating model-translated {model} field {field.id}: {e}"
            )
