import uuid

from django.conf import settings
from django.core.files import File

from apps.files.models import Image


def get_test_image_file() -> File:
    """Return a dummy test image file."""
    return File(
        open(f"{settings.BASE_DIR}/assets/test_image.png", "rb")  # noqa : SIM115
    )


def get_test_image() -> Image:
    """Return an Image instance."""
    image = Image(name=f"{uuid.uuid4()}.png", file=get_test_image_file())
    image._upload_to = lambda instance, filename: image.name
    image.save()
    return image
