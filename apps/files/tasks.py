from projects.celery import app

from .models import Image


@app.task(name="apps.files.tasks.delete_orphan_images")
def delete_orphan_images(threshold: int = None):
    """Delete all orphan image according to `IMAGE_ORPHAN_THRESHOLD_SECONDS` settings.

    Parameters
    ----------
    threshold: int, optional
        Time (in seconds) after which an image is considered an orphan if it
        was not assigned to any model. Default to
        `settings.IMAGE_ORPHAN_THRESHOLD_SECONDS`.
    """

    qs = Image.get_orphan_images(threshold)
    deleted = list(qs.values_list("pk", flat=True))
    qs.delete()
    return deleted
