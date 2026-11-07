from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.commons.mixins import OrganizationRelated
from apps.skills.models import Tag
from services.translator.mixins import HasAutoTranslatedFields


class TeachingDomain(models.Model):
    """
    models to add domain to a teaching
    """

    domain = models.ForeignKey(Tag, on_delete=models.CASCADE)
    teaching = models.ForeignKey(
        "crisalid.Teaching",
        on_delete=models.CASCADE,
        related_name="teaching_domains",
    )
    level = models.SmallIntegerField(
        default=0, validators=(MinValueValidator(0), MaxValueValidator(100))
    )

    class Meta:
        ordering = ("level",)
        constraints = (
            # only one researcher by domains
            models.UniqueConstraint(
                "domain",
                "teaching",
                name="unique_domain_teaching",
            ),
        )
        verbose_name_plural = "TeachingDomains"

    def __str__(self) -> str:
        return f"{self.domain} level={self.level}"

    def __repr__(self):
        return f"<TeachingDomains pk={self.pk} {str(self)} >"


class Teaching(HasAutoTranslatedFields, OrganizationRelated, models.Model):
    """models to represent teaching course by researcher"""

    auto_translated_fields = ["name", "description", "spec"]

    name = models.CharField(max_length=255, null=False, blank=False)
    description = models.TextField(blank=True, null=True)
    spec = models.TextField(blank=True, null=True)

    level = models.TextField(blank=True, null=True)

    link = models.URLField(blank=True, null=True)

    domains = models.ManyToManyField(
        Tag, through=TeachingDomain, related_name="teachings"
    )

    researcher = models.ForeignKey(
        "crisalid.Researcher", on_delete=models.CASCADE, related_name="teachings"
    )

    def __str__(self) -> str:
        return f"{self.name} level={self.level}"

    def __repr__(self):
        return f"<Teaching pk={self.pk} researcher={self.researcher_id} {str(self)} >"

    def get_related_organizations(self):
        return self.researcher.get_related_organizations()
