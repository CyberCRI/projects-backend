from django.db import models

from services.translator.mixins import HasAutoTranslatedFields


class Patent(HasAutoTranslatedFields, models.Model):
    """parent representions (WIP)"""

    auto_translated_fields = ["name", "description"]

    name = models.CharField(max_length=255, null=False, blank=False)
    description = models.TextField(null=True, blank=True)
    date = models.DateField(null=True, blank=True)
    link = models.URLField(null=True, blank=True)

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"<Patent pk={self.pk} {self.name!r}>"


class PatentContributor(models.Model):
    researcher = models.ForeignKey(
        "crisalid.Researcher",
        on_delete=models.CASCADE,
        related_name="patents_conributor",
    )
    patent = models.ForeignKey(Patent, on_delete=models.CASCADE)

    # TODO(remi): add researcher role in this patent ?

    def __repr__(self):
        return f"<PatentContributor pk={self.pk} researcher={self.researcher_id} award={self.patent}>"
