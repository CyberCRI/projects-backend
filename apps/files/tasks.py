from projects.celery import app

from .models import Image


@app.task
def delete_orphan_images(threshold: int = None):
    """Delete all orphan image according to `IMAGE_ORPHAN_THRESHOLD_SECONDS` settings.

    Parameters
    ----------
    threshold: int, optional
        Time (in seconds) after which an image is considered an orphan if it
        was not assigned to any model. Default to
        `settings.IMAGE_ORPHAN_THRESHOLD_SECONDS`.
    """
    deleted = []
    for image in Image.get_orphan_images(threshold):
        deleted.append(image.pk)
        image.delete()  # Delete the DB entry
    return deleted
