import datetime
import uuid
from typing import TYPE_CHECKING, List, Optional

from django.apps import apps
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import models, transaction
from django.db.models import ForeignObjectRel, Model, Q, QuerySet
from django.utils import timezone
from simple_history.models import HistoricalRecords
from stdimage import StdImageField

from apps.commons.mixins import (
    DuplicableModel,
    HasOwner,
    OrganizationRelated,
    ProjectRelated,
)

from .enums import AttachmentLinkCategory, AttachmentType
from .utils import resize_and_autorotate

if TYPE_CHECKING:
    from apps.accounts.models import ProjectUser
    from apps.organizations.models import Organization
    from apps.projects.models import Project

MAX_IMAGE_HEIGHT = 10000


def dynamic_upload_to(instance: Model, filename: str):
    assert hasattr(instance, "_upload_to"), (
        "Instance of '%s' using this function as callable for an `upload_to` "
        "argument should have a dynamic attribute `_upload_to` set before "
        "saving it for the first time." % instance.__class__.__name__
    )
    upload_to = instance.__dict__.pop("_upload_to")
    return upload_to(instance, filename)


def attachment_link_preview_path(instance, filename: str):
    date_part = f"{datetime.datetime.today():%Y-%m-%d}"
    return (
        f"project/attachments/{instance.project.pk}/link/preview/{date_part}-{filename}"
    )


def organization_attachment_directory_path(instance: "OrganizationAttachmentFile", filename: str):
    date_part = f"{datetime.datetime.today():%Y-%m-%d}"
    return f"organization/attachments/{instance.organization.pk}/{instance.attachment_type}/{date_part}-{filename}"


def attachment_directory_path(instance: "AttachmentFile", filename: str):
    date_part = f"{datetime.datetime.today():%Y-%m-%d}"
    return f"project/attachments/{instance.project.pk}/{instance.attachment_type}/{date_part}-{filename}"


class AttachmentLink(
    models.Model, ProjectRelated, OrganizationRelated, DuplicableModel
):
    project = models.ForeignKey(
        "projects.Project", on_delete=models.CASCADE, related_name="links"
    )
    attachment_type = models.CharField(
        max_length=10, choices=AttachmentType.choices, default=AttachmentType.LINK
    )
    category = models.CharField(
        max_length=50,
        choices=AttachmentLinkCategory.choices,
        default=AttachmentLinkCategory.OTHER,
    )
    description = models.TextField(blank=True)
    preview_image_url = models.URLField(
        max_length=2048, help_text="attachment link preview image, mostly thumbnails"
    )
    site_name = models.CharField(max_length=255)
    site_url = models.URLField(max_length=2048)
    title = models.CharField(max_length=255, blank=True)
    history = HistoricalRecords()

    @transaction.atomic
    def save(self, *args, **kwargs):
        create = self.pk is None
        super().save(*args, **kwargs)
        if create and hasattr(self.project, "stat"):
            self.project.stat.update_links()

    @transaction.atomic
    def delete(self, using=None, keep_parents=False):
        project = self.project
        super().delete(using, keep_parents)
        if hasattr(project, "stat"):
            project.stat.update_links()

    def get_related_organizations(self) -> List["Organization"]:
        """Return the organizations related to this model."""
        return self.project.get_related_organizations()

    def get_related_project(self) -> Optional["Project"]:
        """Return the project related to this model."""
        return self.project

    def duplicate(self, project: "Project") -> "AttachmentLink":
        return AttachmentLink.objects.create(
            project=project,
            attachment_type=self.attachment_type,
            category=self.category,
            description=self.description,
            preview_image_url=self.preview_image_url,
            site_name=self.site_name,
            site_url=self.site_url,
            title=self.title,
        )


class OrganizationAttachmentFile(models.Model, OrganizationRelated):
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="attachment_files",
    )
    attachment_type = models.CharField(
        max_length=10, choices=AttachmentType.choices, default=AttachmentType.FILE
    )
    file = models.FileField(upload_to=organization_attachment_directory_path)
    mime = models.CharField(max_length=100)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    hashcode = models.CharField(max_length=64, default="")

    def get_related_organizations(self) -> List["Organization"]:
        """Return the organizations related to this model."""
        return [self.organization]


class AttachmentFile(
    models.Model, ProjectRelated, OrganizationRelated, DuplicableModel
):
    project = models.ForeignKey(
        "projects.Project", on_delete=models.CASCADE, related_name="files"
    )
    attachment_type = models.CharField(
        max_length=10, choices=AttachmentType.choices, default=AttachmentType.FILE
    )
    file = models.FileField(upload_to=attachment_directory_path)
    mime = models.CharField(max_length=100)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    hashcode = models.CharField(max_length=64, default="")
    history = HistoricalRecords()

    @transaction.atomic
    def save(self, *args, **kwargs):
        create = self.pk is None
        super().save(*args, **kwargs)
        if create and hasattr(self.project, "stat"):
            self.project.stat.update_files()

    @transaction.atomic
    def delete(self, using=None, keep_parents=False):
        project = self.project
        super().delete(using, keep_parents)
        if hasattr(project, "stat"):
            project.stat.update_files()

    def get_related_organizations(self) -> List["Organization"]:
        """Return the organizations related to this model."""
        return self.project.get_related_organizations()

    def get_related_project(self) -> Optional["Project"]:
        """Return the project related to this model."""
        return self.project

    def duplicate(self, project: "Project") -> "AttachmentFile":
        file_path = self.file.name.split("/")
        file_name = file_path.pop()
        file_extension = file_name.split(".")[-1]
        new_name = "/".join([*file_path, f"{uuid.uuid4()}.{file_extension}"])
        new_file = SimpleUploadedFile(
            name=new_name,
            content=self.file.read(),
            content_type=f"application/{file_extension}",
        )
        return AttachmentFile.objects.create(
            project=project,
            attachment_type=self.attachment_type,
            file=new_file,
            mime=self.mime,
            title=self.title,
            description=self.description,
            hashcode=self.hashcode,
        )


class Image(
    models.Model, HasOwner, OrganizationRelated, ProjectRelated, DuplicableModel
):
    name = models.CharField(max_length=255)
    file = StdImageField(
        upload_to=dynamic_upload_to,
        height_field="height",
        width_field="width",
        render_variations=resize_and_autorotate,
        variations={
            "full": (1920, MAX_IMAGE_HEIGHT),
            "large": (1024, MAX_IMAGE_HEIGHT),
            "medium": (768, MAX_IMAGE_HEIGHT),
            "small": (500, MAX_IMAGE_HEIGHT),
        },
        delete_orphans=True,
    )
    height = models.IntegerField(blank=True, null=True)
    width = models.IntegerField(blank=True, null=True)
    natural_ratio = models.FloatField(blank=True, null=True)
    scale_x = models.FloatField(blank=True, null=True)
    scale_y = models.FloatField(blank=True, null=True)
    left = models.FloatField(blank=True, null=True)
    top = models.FloatField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    owner = models.ForeignKey(
        "accounts.ProjectUser",
        on_delete=models.CASCADE,
        related_name="images",
        null=True,
    )

    @classmethod
    def get_orphan_images(cls, threshold: Optional[int] = None) -> QuerySet:
        """Return a QuerySet containing all the orphan images.

        Parameters
        ----------
        threshold: int, optional
            Time (in seconds) after which an image is considered an orphan if it
            was not assigned to any model. Default to
            `settings.IMAGE_ORPHAN_THRESHOLD_SECONDS`.
        """
        if threshold is None:
            threshold = settings.IMAGE_ORPHAN_THRESHOLD_SECONDS
        filters = {
            f.name: None
            for f in cls._meta.get_fields()
            if isinstance(f, ForeignObjectRel)
        }
        threshold = timezone.localtime(timezone.now()) - datetime.timedelta(
            seconds=threshold
        )
        return Image.objects.filter(created_at__lt=threshold, **filters)

    def is_owned_by(self, user: "ProjectUser") -> bool:
        """Whether the given user is the owner of the object."""
        if self.user.exists():
            return self.user.get() == user
        return self.owner == user

    def get_owner(self):
        """Get the owner of the object."""
        if self.user.exists():
            return self.user.get()
        return self.owner

    def get_related_organizations(self) -> List["Organization"]:
        """Return the organizations related to this model."""
        related_project = self.get_related_project()
        if related_project:
            return related_project.get_related_organizations()
        if self.user.exists():
            return self.user.get().get_related_organizations()
        Organization = apps.get_model("organizations", "Organization")  # noqa
        return list(
            Organization.objects.filter(
                Q(images=self)
                | Q(logo_image=self)
                | Q(banner_image=self)
                | Q(project_categories__background_image=self)
                | Q(project_categories__template__images=self)
                | Q(people_groups__header_image=self)
                | Q(people_groups__logo_image=self)
                | Q(news__header_image=self)
                | Q(news__images=self)
                | Q(instructions__images=self)
                | Q(events__images=self)
            ).distinct()
        )

    def get_related_project(self) -> Optional["Project"]:
        """
        Return the project related to this model.

        With the current data format, an image should be related to only one project.
        However, with the old duplication version, the same Image object could be
        related to multiple projects. In this case, we return the first project
        found.

        TODO : Actually duplicate the old images to avoid this issue and replace
        `first()` by `get()`.
        """
        Project = apps.get_model("projects", "Project")  # noqa
        queryset = Project.objects.filter(
            Q(header_image=self)
            | Q(images=self)
            | Q(blog_entries__images=self)
            | Q(comments__images=self)
            | Q(messages__images=self)
            | Q(additional_tabs__images=self)
            | Q(additional_tabs__items__images=self)
        ).distinct()
        if queryset.exists():
            return queryset.first()
        return None

    def duplicate(
        self, owner: Optional["ProjectUser"] = None, upload_to: str = ""
    ) -> "Image":
        file_path = self.file.name.split("/")
        file_name = file_path.pop()
        file_extension = file_name.split(".")[-1]
        if upload_to:
            upload_to = f"{upload_to}{uuid.uuid4()}.{file_extension}"
        else:
            upload_to = "/".join([*file_path, f"{uuid.uuid4()}.{file_extension}"])
        new_file = SimpleUploadedFile(
            name=upload_to,
            content=self.file.read(),
            content_type=f"image/{file_extension}",
        )
        image = Image(
            name=self.name,
            file=new_file,
            height=self.height,
            width=self.width,
            natural_ratio=self.natural_ratio,
            scale_x=self.scale_x,
            scale_y=self.scale_y,
            left=self.left,
            top=self.top,
            owner=owner or self.owner,
        )
        image._upload_to = lambda instance, filename: upload_to
        image.save()
        return image

