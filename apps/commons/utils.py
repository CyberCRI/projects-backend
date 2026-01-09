import base64
import gc
import io
import itertools
import uuid
from contextlib import suppress
from typing import TYPE_CHECKING, List, Optional, Tuple

from bs4 import BeautifulSoup
from django.conf import settings
from django.contrib.postgres.fields import ArrayField
from django.core.files import File
from django.core.files.base import ContentFile
from django.db import reset_queries
from django.db.models import Func, Model, Value
from django.forms import IntegerField
from django.urls import reverse
from PIL import Image as PILImage

from apps.files.models import Image

if TYPE_CHECKING:
    from apps.accounts.models import ProjectUser


class BeautifulSoupProjects(BeautifulSoup):
    """wrapper around BeautifulSoup with lxml with default parser, and guard clause around empty body"""

    def __init__(self, text: str):
        super().__init__(text, "lxml")

    def __str__(self) -> str:
        if self.body:
            return self.body.decode_contents()
        return ""


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


def iter_img_b64(soup: BeautifulSoup):
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if src.startswith("data:image") and ";base64," in src:
            yield img


def remove_images_text(text: str) -> str:
    """Process rich text sent by the frontend.
    Some texts can contain images

    Parameters
    ----------
    text : str
        The text to process.

    Returns
    -------
    str
        The processed text whitout images.
    """
    soup = BeautifulSoupProjects(text)

    for img in iter_img_b64(soup):
        img.decompose()
    return str(soup)


def process_text(
    text: str,
    instance: Model | None = None,
    upload_to: str | None = None,
    view: str | None = None,
    owner: Optional["ProjectUser"] = None,
    process_template: bool = False,
    **kwargs,
) -> tuple[str, list[Image]]:
    """
    Process rich text sent by the frontend.
    Some texts can contain images that must be duplicated or linked to the instance :
    - Base64 images are uploaded to the storage and linked to the instance.
    - Template images are duplicated and linked to the instance.
    - Unlinked images are linked to the instance.

    Parameters
    ----------
    instance : Model
        The instance where the text is located.
    text : str
        The text to process.
    upload_to : str
        The path where the images will be uploaded in the storage.
    view : str
        The name of the view to retrieve the image after processing.
    process_template : bool, optional
        Whether to look for images coming from templates, by default False
    owner : ProjectUser, optional
        The owner of the instance.
    forbid_images : bool, optional
        Whether to forbid images in the text, by default False
    kwargs
        Additional arguments to pass to the view to build the image url

    Returns
    -------
    Tuple[str, List[Image]]
        The processed text and the images to link to the instance.
    """

    assert all(
        (instance, upload_to, view)
    ), "instance, upload_to and view parameters are required."

    soup = BeautifulSoupProjects(text)

    if process_template:
        soup, template_images = process_template_images(
            soup, upload_to, view, owner, **kwargs
        )
    else:
        template_images = []

    unlinked_images = process_unlinked_images(instance, soup)
    soup, base_64_images = process_base64_images(soup, upload_to, view, owner, **kwargs)
    images = list(set(template_images + unlinked_images + base_64_images))
    return str(soup), images


def process_base64_images(
    soup: BeautifulSoupProjects,
    upload_to: str,
    view: str,
    owner: Optional["ProjectUser"] = None,
    **kwargs,
) -> tuple[str, list[Image]]:
    """
    Process base64 images in the text.

    Parameters
    ----------
    text : str
        The text to process.
    upload_to : str
        The path where the images will be uploaded in the storage.
    view : str
        The name of the view to retrieve the image after processing.
    owner : ProjectUser, optional
        The owner of the instance.
    kwargs
        Additional arguments to pass to the view to build the image url

    Returns
    -------
    Tuple[str, List[Image]]
        The processed text and the images to link to the instance.
    """
    images = []
    for img in iter_img_b64(soup):
        info, data = img["src"].split("base64,", 1)
        mediatype, *_ = info.removeprefix("data:").split(";")
        extension = mediatype.split("/")[-1]
        file = ContentFile(
            base64.b64decode(data), name=str(f"{uuid.uuid4()}.{extension}")
        )
        image = Image(name=file.name, file=file, owner=owner)
        image._upload_to = lambda *args: f"{upload_to}{file.name}"  # noqa: B023
        image.save()
        images.append(image)

        # replace base64 to url
        img["src"] = reverse(view, kwargs={"pk": image.pk, **kwargs})

    return soup, images


def process_template_images(
    soup: BeautifulSoupProjects,
    upload_to: str,
    view: str,
    owner: Optional["ProjectUser"] = None,
    **kwargs,
) -> tuple[BeautifulSoupProjects, list[Image]]:
    """
    Process template images in the text.

    Parameters
    ----------
    text : str
        The text to process.
    upload_to : str
        The path where the images will be uploaded in the storage.
    view : str
        The name of the view to retrieve the image after processing.
    owner : ProjectUser, optional
        The owner of the instance.
    kwargs
        Additional arguments to pass to the view to build the image url

    Returns
    -------
    Tuple[str, List[Image]]
        The processed text and the images to link to the instance.
    """
    images = []
    for img in soup.find_all("img"):
        image_url = img["src"]
        if (
            image_url.startswith("/v1/organization/")
            and "/template/" in image_url
            and "/image/" in image_url
        ):
            image_id = (
                image_url.split("/")[-1]
                if image_url[-1] != "/"
                else image_url.split("/")[-2]
            )

            with suppress(Image.DoesNotExist):
                image = Image.objects.get(id=image_id)
                new_image = image.duplicate(owner=owner, upload_to=upload_to)
                if new_image is not None:
                    images.append(new_image)
                    img["src"] = reverse(view, kwargs={"pk": new_image.pk, **kwargs})

    return soup, images


def process_unlinked_images(
    instance: Model, text: BeautifulSoupProjects | str
) -> list[Image]:
    """
    Find images in the text that are not linked to the instance.

    Parameters
    ----------
    instance : Model
        The instance where the text is located.
    text : BeautifulSoupProjects | str
        The text to process.

    Returns
    -------
    List[Image]
        The images to link to the instance.
    """
    if isinstance(text, str):
        soup = BeautifulSoupProjects(text)
    else:
        soup = text

    images_ids = []
    for image_tag in soup.find_all("img"):
        image_url = image_tag["src"]
        if image_url.startswith("/v1"):
            image_id = (
                image_url.split("/")[-1]
                if image_url[-1] != "/"
                else image_url.split("/")[-2]
            )
            images_ids.append(image_id)

    # get all images already created but not linked to instances
    images = Image.objects.filter(id__in=images_ids).exclude(
        id__in=instance.images.all()
    )
    return list(images)


def get_test_image_file() -> File:
    """Return a dummy test image file."""
    thumb_io = io.BytesIO()
    with PILImage.new("RGB", [1, 1]) as thumb:
        thumb.save(thumb_io, format="JPEG")
    data = thumb_io.getvalue()
    return File(ContentFile(data), name=f"{uuid.uuid4()}.jpg")


def get_test_image() -> Image:
    """Return an Image instance."""
    image = Image(name=f"{uuid.uuid4()}.png", file=get_test_image_file())
    image._upload_to = lambda instance, filename: image.name
    image.save()
    return image


def get_permissions_from_subscopes(
    subscopes: List[Tuple[str, str]],
) -> Tuple[Tuple[str, str]]:
    """
    Get the permissions representations from the subscopes.

    Parameters
    ----------
    subscopes : List[Tuple[str, str]]
        The subscopes to generate the permissions from.

    Returns
    -------
    Tuple[Tuple[str, str]]
        The permissions representations
    """
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


def get_write_permissions_from_subscopes(
    subscopes: List[Tuple[str, str]],
) -> Tuple[Tuple[str, str]]:
    """
    Get the write permissions representations from the subscopes.

    Parameters
    ----------
    subscopes : List[Tuple[str, str]]
        The subscopes to generate the permissions from.

    Returns
    -------
    Tuple[Tuple[str, str]]
        The write permissions representations
    """
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
    """
    Map an HTTP action and a model codename to a permission representation.

    Parameters
    ----------
    action : str
        The HTTP action.
    codename : str
        The codename of the model.

    Returns
    -------
    Optional[str]
        The permission representation.
    """
    return {
        "list": f"view_{codename}",
        "retrieve": f"view_{codename}",
        "create": f"add_{codename}",
        "update": f"change_{codename}",
        "partial_update": f"change_{codename}",
        "destroy": f"delete_{codename}",
    }.get(action)


def clear_memory(func):
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        if settings.FORCE_CLEAN_DB_CACHE:
            reset_queries()
        if settings.FORCE_GARBAGE_COLLECT:
            gc.collect()
        return result

    return wrapper
