import datetime
from typing import TYPE_CHECKING, List

from django.apps import apps
from django.conf import settings
from django.db import models, transaction
from django.db.models import ForeignObjectRel, Model, Q, QuerySet
from django.utils import timezone
from simple_history.models import HistoricalRecords
from pictures.models import PictureField

from apps.commons.db.abc import HasOwner, OrganizationRelated, ProjectRelated
from apps.files.enums import AttachmentLinkCategory, AttachmentType
from apps.files.utils import resize_and_autorotate

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


def attachment_directory_path(instance, filename: str):
    date_part = f"{datetime.datetime.today():%Y-%m-%d}"
    return f"project/attachments/{instance.project.pk}/{instance.attachment_type}/{date_part}-{filename}"


class AttachmentLink(models.Model, ProjectRelated, OrganizationRelated):
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

    def get_related_projects(self) -> List["Project"]:
        """Return the project related to this model."""
        return [self.project]


class AttachmentFile(models.Model, ProjectRelated, OrganizationRelated):
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

    def get_related_projects(self) -> List["Project"]:
        """Return the project related to this model."""
        return [self.project]


class Image(models.Model, HasOwner, OrganizationRelated, ProjectRelated):
    name = models.CharField(max_length=255)
    file = PictureField(
        upload_to=dynamic_upload_to,
        height_field="height",
        width_field="width",
        aspect_ratios=[None, "1/1", "4/3", "16/9"],
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
        to_field="keycloak_id",
        null=True,
    )

    @classmethod
    def get_orphan_images(cls, threshold: int = None) -> QuerySet:
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
        threshold = timezone.now() - datetime.timedelta(seconds=threshold)
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
        Organization = apps.get_model("organizations", "Organization")  # noqa
        if self.organization_logo.exists():
            return [self.organization_logo.get()]
        if self.organization_banner.exists():
            return [self.organization_banner.get()]
        if self.organizations.exists():
            return [self.organizations.get()]
        if self.faqs.exists():
            return [self.faqs.get().organization]
        if self.project_category.exists():
            return [self.project_category.get().organization]
        if self.project_header.exists():
            return self.project_header.get().organizations.all()
        if self.projects.exists():
            return self.projects.get().organizations.all()
        if self.blog_entries.exists():
            return self.blog_entries.get().project.organizations.all()
        if self.comments.exists():
            return self.comments.get().project.organizations.all()
        if self.user.exists():
            return Organization.objects.filter(groups__in=self.user.get().groups.all())
        if self.people_group_logo.exists():
            return [self.people_group_logo.get().organization]
        if self.people_group_header.exists():
            return [self.people_group_header.get().organization]
        return []

    def get_related_projects(self) -> List["Project"]:
        """Return the projects related to this model."""
        Project = apps.get_model("projects", "Project")  # noqa
        return Project.objects.filter(
            (Q(header_image=self) | Q(images=self))
            | Q(blog_entries__images=self)
            | Q(comments__images=self)
        )


class PeopleResource(models.Model):
    people_id = models.CharField(max_length=255)
    people_data = models.JSONField(default=dict)
