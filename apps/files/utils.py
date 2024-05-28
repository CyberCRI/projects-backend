from io import BytesIO

from django.core.files.base import ContentFile
from PIL import Image
from stdimage.utils import render_variations


def resize_and_autorotate(file_name, variations, storage):
    with (
        storage.open(file_name) as f,
        Image.open(f) as image,
        BytesIO() as file_buffer,
    ):
        if not image.is_animated:
            file_format = image.format
            try:
                exif = image._getexif()
            except AttributeError:  # Some images formats don't implement _getexif
                exif = None
            # if image has exif data about orientation, rotate it
            orientation_key = 274  # cf ExifTags
            if exif and orientation_key in exif:
                orientation = exif[orientation_key]

                rotate_values = {
                    3: Image.ROTATE_180,
                    6: Image.ROTATE_270,
                    8: Image.ROTATE_90,
                }

                if orientation in rotate_values:
                    image = image.transpose(rotate_values[orientation])

            image.save(file_buffer, file_format)
            f = ContentFile(file_buffer.getvalue())
            storage.delete(file_name)
            storage.save(file_name, f)
        # render stdimage variations
        render_variations(file_name, variations, replace=True, storage=storage)
    return False  # prevent default rendering
