import base64
import re
import uuid

from bs4 import BeautifulSoup
from django.core.files.base import ContentFile
from django.urls import reverse

from apps.files.models import Image


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
