import hashlib
import mimetypes

import factory
from django.core.files.uploadedfile import SimpleUploadedFile
from faker import Faker

from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory

from .models import (
    AttachmentFile,
    AttachmentLink,
    AttachmentLinkCategory,
    AttachmentType,
    OrganizationAttachmentFile,
    PeopleGroupImage,
)

faker = Faker()


def get_random_binary_file(size: int = 128) -> bytes:
    return SimpleUploadedFile(
        faker.file_name(extension="dat"),
        faker.binary(size),
        content_type="text/plain",
    )


class OrganizationAttachmentFileFactory(factory.django.DjangoModelFactory):
    organization = factory.LazyFunction(
        lambda: OrganizationFactory()
    )  # Subfactory seems to not trigger `create()`
    attachment_type = AttachmentType.FILE
    file = factory.django.FileField(
        filename="file.dat", from_func=get_random_binary_file
    )
    mime = "application/octet-stream"
    title = factory.Faker("sentence")

    @factory.lazy_attribute
    def hashcode(self):
        hashcode = hashlib.sha256(self.file.read()).hexdigest()
        self.file.seek(0)
        return hashcode

    class Meta:
        model = OrganizationAttachmentFile


class AttachmentFileFactory(factory.django.DjangoModelFactory):
    project = factory.LazyFunction(
        lambda: ProjectFactory()
    )  # Subfactory seems to not trigger `create()`
    attachment_type = AttachmentType.FILE
    file = factory.django.FileField(
        filename="file.dat", from_func=get_random_binary_file
    )
    mime = "application/octet-stream"
    title = factory.Faker("sentence")

    @factory.lazy_attribute
    def hashcode(self):
        hashcode = hashlib.sha256(self.file.read()).hexdigest()
        self.file.seek(0)
        return hashcode

    class Meta:
        model = AttachmentFile


class AttachmentLinkFactory(factory.django.DjangoModelFactory):
    project = factory.LazyFunction(
        lambda: ProjectFactory()
    )  # Subfactory seems to not trigger `create()`
    attachment_type = AttachmentType.LINK
    category = AttachmentLinkCategory.OTHER
    preview_image_url = factory.Faker("url")
    site_name = factory.Faker("word")
    site_url = factory.Faker("url")

    class Meta:
        model = AttachmentLink


def get_image_file():
    image_data = faker.image((1, 1), image_format="jpeg")
    return SimpleUploadedFile(
        "img.jpeg", image_data, content_type=mimetypes.types_map[".jpeg"]
    )


class PeopleGroupImageFactory(factory.django.DjangoModelFactory):
    name = factory.Faker("word")

    file = factory.django.FileField(
        filename="img.jpeg", from_func=get_image_file
    )

    class Meta:
        model = PeopleGroupImage
