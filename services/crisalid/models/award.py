from django.db import models

from services.translator.mixins import HasAutoTranslatedFields


class Award(HasAutoTranslatedFields, models.Model):
    """Award representions (WIP)"""

    auto_translated_fields = ["name", "description"]

    name = models.CharField(max_length=255, null=False, blank=False)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"<Award pk={self.pk} {self.name!r}>"


class AwardContributor(models.Model):
    researcher = models.ForeignKey(
        "crisalid.Researcher",
        on_delete=models.CASCADE,
        related_name="awards_conributor",
    )
    award = models.ForeignKey(Award, on_delete=models.CASCADE)
    description = models.TextField(null=True, blank=True)

    date = models.DateField(null=True, blank=True)
    link = models.URLField(null=True, blank=True)

    def __repr__(self):
        return f"<AwardContributor pk={self.pk} researcher={self.researcher_id} award={self.award_id}>"
