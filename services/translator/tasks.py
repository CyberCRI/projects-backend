from apps.commons.utils import clear_memory
from projects.celery import app

from .models import AutoTranslatedField
from .utils import update_auto_translated_field


@app.task(name="apps.translations.tasks.automatic_translations")
@clear_memory
def automatic_translations():
    for field in AutoTranslatedField.objects.filter(up_to_date=False, is_active=True):
        update_auto_translated_field(field)
