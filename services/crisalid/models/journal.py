from django.contrib.postgres.fields import ArrayField
from django.db import models

from services.crisalid.manager import CrisalidQuerySet


class Journal(models.Model):
    """representations of a journal models (from crisalid)
    https://github.com/CRISalid-esr/crisalid-ikg/blob/dev-main/app/models/publication_channel.py#L6
    """

    title = models.CharField(max_length=255)
    acronym = ArrayField(models.CharField(max_length=255), default=list)

    objects = CrisalidQuerySet.as_manager()

    def __str__(self):
        return f"{self.title} ({self.acronym!r})"

    def __repr__(self):
        return f"<Journal pk={self.pk} title={self.title}>"
