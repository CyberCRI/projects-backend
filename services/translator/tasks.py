import logging

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
