import hashlib

import factory

from apps.projects.factories import ProjectFactory

from .models import (
    AttachmentFile,
    AttachmentLink,
    AttachmentLinkCategory,
    AttachmentType,
)


class AttachmentFileFactory(factory.django.DjangoModelFactory):
    project = factory.LazyFunction(
        lambda: ProjectFactory()
    )  # Subfactory seems to not trigger `create()`
    attachment_type = AttachmentType.FILE
    file = factory.django.FileField(filename="file.dat", data=b"content")
    mime = factory.Faker("text", max_nb_chars=100)
    title = factory.Faker("text", max_nb_chars=255)
    hashcode = hashlib.sha256(b"content").hexdigest()

    class Meta:
        model = AttachmentFile


class AttachmentLinkFactory(factory.django.DjangoModelFactory):
    project = factory.LazyFunction(
        lambda: ProjectFactory()
    )  # Subfactory seems to not trigger `create()`
    attachment_type = AttachmentType.LINK
    category = AttachmentLinkCategory.OTHER
    preview_image_url = "https://as1.ftcdn.net/v2/jpg/01/13/96/70/1000_F_113967069_We6GnlQl7icXaoKIVreKLpZIM4xSQEwn.jpg"
    site_name = factory.Faker("text", max_nb_chars=255)
    site_url = "google.com"

    class Meta:
        model = AttachmentLink
