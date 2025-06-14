import hashlib

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
    mime = factory.Faker("text", max_nb_chars=100)
    title = factory.Faker("text", max_nb_chars=255)

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
    mime = factory.Faker("text", max_nb_chars=100)
    title = factory.Faker("text", max_nb_chars=255)

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
    site_name = factory.Faker("text", max_nb_chars=255)
    site_url = factory.Faker("url")

    class Meta:
        model = AttachmentLink
