from django.db import models

from apps.commons.mixins import HasOwner
from services.translator.mixins import HasAutoTranslatedFields


class Patent(HasAutoTranslatedFields, HasOwner, models.Model):
    """parent representions (WIP)"""

    auto_translated_fields = ["name", "description"]

    name = models.CharField(max_length=255, null=False, blank=False)
    description = models.TextField(null=True, blank=True)

    date = models.DateField(null=True, blank=True)
    link = models.URLField(null=True, blank=True)

    researcher = models.ForeignKey(
        "crisalid.Researcher", on_delete=models.CASCADE, related_name="patents"
    )

    def __str__(self):
        return f"{self.name} {self.date or ''}"

    def __repr__(self):
        return f"<Patent pk={self.pk} researcher={self.researcher_id} {self.name!r}>"

    def get_owner(self):
        return self.researcher.get_owner()
