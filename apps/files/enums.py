from django.db.models import TextChoices


class AttachmentLinkCategory(TextChoices):
    """Allowed `AttachmentLink` categories."""

    PROJECT_WEBSITE = "project_website"
    DOCUMENTARY_RESOURCE = "documentary_resource"
    INSPIRATION = "inspiration"
    DATA = "data"
    PUBLICATION = "publication"
    SOURCE_CODE = "source_code"
    TOOL = "tool"
    OTHER = "other"


class AttachmentType(TextChoices):
    """Allowed `Attachment*` types."""

    FILE = "file"
    IMAGE = "image"
    VIDEO = "video"
    LINK = "link"
