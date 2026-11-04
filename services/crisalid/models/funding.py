from django.db import models

from apps.commons.mixins import ProjectRelated
from services.translator.mixins import HasAutoTranslatedFields


class Funding(HasAutoTranslatedFields, ProjectRelated, models.Model):
    """models to represent funding by researcher"""

    auto_translated_fields = ["name", "description"]

    name = models.CharField(max_length=255, null=False, blank=False)
    description = models.TextField(blank=True, null=True)

    class Currency(models.TextChoices):
        EUR = "EUR"
        USD = "USD"

    prices = models.PositiveBigIntegerField(blank=True, null=True)
    currency = models.CharField(
        default=None, choices=Currency.choices, blank=True, null=True
    )
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    project = models.ForeignKey(
        "projects.Project",
        null=True,
        on_delete=models.SET_NULL,
        related_name="fundings",
    )

    researchers = models.ManyToManyField("crisalid.Researcher", related_name="fundings")

    def __str__(self) -> str:
        return f"{self.name} prices={self.prices}"

    def __repr__(self):
        return f"<Funding pk={self.pk} projet={self.projet_id} {str(self)} >"

    def get_related_project(self):
        return self.project
