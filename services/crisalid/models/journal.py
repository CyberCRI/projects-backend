from django.contrib.postgres.fields import ArrayField
from django.db import models


class Journal(models.Model):
    """representations of a journal models (from crisalid)
    https://github.com/CRISalid-esr/crisalid-ikg/blob/dev-main/app/models/publication_channel.py#L6
    """

    uid = models.CharField(max_length=255, blank=True, null=True)
    title = models.CharField(max_length=255)
    acronym = ArrayField(models.CharField(max_length=255), default=list)

    def __str__(self):
        return f"{self.title} ({self.acronym!r})"

    def __repr__(self):
        return f"<Journal pk={self.pk} uid={self.uid} title={self.title}>"
