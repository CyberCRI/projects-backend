import base64
import itertools
import re
import uuid
from typing import Optional

from bs4 import BeautifulSoup
from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.core.files import File
from django.core.files.base import ContentFile
from django.db.models import Func, Value
from django.forms import IntegerField
from django.urls import reverse

from apps.files.models import Image


class ArrayPosition(Func):
    """Allows to order the rows through a list of column's value.

    Only works with Postgresql.

    Examples
    --------
    >>> qs = Project.objects.all()
    >>> qs = qs.annotate(ordering=ArrayPosition(pk_list, F('pk'))
    >>> qs = qs.order_by('ordering')
    """

    function = "array_position"

    def __init__(
        self, items, *expressions, base_field=None, output_field=None, **extra
    ):
        if base_field is None:
            base_field = IntegerField()
        if output_field is None:
            output_field = base_field

        first_arg = Value(list(items), output_field=ArrayField(base_field))
        expressions = (first_arg,) + expressions
        super().__init__(*expressions, output_field=output_field, **extra)


def process_text(request, instance, text, upload_to, view, **kwargs):
    unlinked_images = process_unlinked_images(instance, text)
    text, base_64_images = process_base64_images(
        request, text, upload_to, view, **kwargs
    )
    return text, base_64_images + unlinked_images


def process_base64_images(request, text, upload_to, view, **kwargs):
    base_64_images = re.findall('[\'"]data:image/[^"]*;base64,[^"]*[\'"]', text)
    base_64_images = [data[1:-1] for data in base_64_images]
    images = list()
    for base_64_image in base_64_images:
        data = base_64_image.split(";base64,")
        extension = data[0].split("/")[-1]
        file = ContentFile(
            base64.b64decode(data[1]), name=str(f"{uuid.uuid4()}.{extension}")
        )
        image = Image(name=file.name, file=file, owner=request.user)
        image._upload_to = lambda *args: f"{upload_to}{file.name}"  # noqa : B023
        image.save()
        images.append(image)
        text = text.replace(
            base_64_image,
            reverse(view, kwargs={"pk": image.pk, **kwargs}),
        )
    return text, images


def process_unlinked_images(instance, text):
    soup = BeautifulSoup(text, features="html.parser")
    images_tags = soup.findAll("img")
    images = list()
    for image_tag in images_tags:
        image_url = image_tag["src"]
        if image_url.startswith("/v1"):
            image_id = (
                image_url.split("/")[-1]
                if image_url[-1] != "/"
                else image_url.split("/")[-2]
            )
            image = Image.objects.get(id=image_id)
            if image not in instance.images.all():
                images.append(image)
    return images


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


def get_permissions_from_subscopes(subscopes):
    permissions = (
        (
            ("view_" + subscope[0], "Can view " + subscope[1]),
            ("add_" + subscope[0], "Can add " + subscope[1]),
            ("change_" + subscope[0], "Can change " + subscope[1]),
            ("delete_" + subscope[0], "Can delete " + subscope[1]),
        )
        for subscope in subscopes
    )
    return tuple(itertools.chain.from_iterable(permissions))


def get_write_permissions_from_subscopes(subscopes):
    permissions = (
        (
            ("add_" + subscope[0], "Can add " + subscope[1]),
            ("change_" + subscope[0], "Can change " + subscope[1]),
            ("delete_" + subscope[0], "Can delete " + subscope[1]),
        )
        for subscope in subscopes
    )
    return tuple(itertools.chain.from_iterable(permissions))


def map_action_to_permission(action: str, codename: str) -> Optional[str]:
    return {
        "list": f"view_{codename}",
        "retrieve": f"view_{codename}",
        "create": f"add_{codename}",
        "update": f"change_{codename}",
        "partial_update": f"change_{codename}",
        "destroy": f"delete_{codename}",
    }.get(action, None)
