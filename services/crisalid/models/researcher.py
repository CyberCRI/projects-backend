from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from apps.commons.mixins import (
    HasEmbedding,
    HasOwner,
    HasRelatedModules,
    TimestampedModelMixin,
)
from apps.skills.models import Tag
from services.crisalid.manager import CrisalidQuerySet
from services.crisalid.models.indentifier import Identifier
from services.translator.mixins import HasAutoTranslatedFields


class ResearcherDomains(TimestampedModelMixin, models.Model):
    domain = models.ForeignKey(Tag, on_delete=models.CASCADE)
    researcher = models.ForeignKey(
        "crisalid.Researcher",
        on_delete=models.CASCADE,
        related_name="researcher_domains",
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
                "researcher",
                name="unique_domain_researcher",
            ),
        )
        verbose_name_plural = "ResearcherDomains"

    def __str__(self):
        return f"{self.domain} {self.level}"

    def __repr__(self):
        return f"<ResearcherDomains domain={self.domain} researcher={self.researcher} level={self.level}>"


class Researcher(
    HasRelatedModules,
    HasEmbedding,
    HasOwner,
    TimestampedModelMixin,
    HasAutoTranslatedFields,
):
    """Link to a crisalid"""

    PRIVACY_HARVESTER = (
        Identifier.Harvester.EPPN,
        Identifier.Harvester.PPN,
        Identifier.Harvester.LOCAL,
    )
    auto_translated_fields = ["html:bio", "html:short_bio"]

    user = models.OneToOneField(
        "accounts.ProjectUser",
        on_delete=models.CASCADE,
        related_name="researcher",
        # if no user linked to projects
        null=True,
    )
    given_name = models.CharField(max_length=255, blank=True)
    family_name = models.CharField(max_length=255, blank=True)
    identifiers = models.ManyToManyField(
        "crisalid.Identifier", related_name="researchers"
    )

    domains = models.ManyToManyField(
        Tag, through=ResearcherDomains, related_name="researchers"
    )
    bio = models.TextField(blank=True, null=True, default="")
    short_bio = models.TextField(blank=True, null=True, default="")

    h_index = models.PositiveIntegerField(default=None, null=True, blank=True)
    i10_index = models.PositiveIntegerField(default=None, null=True, blank=True)

    objects = CrisalidQuerySet.as_manager()
    organization_query_string = "user__groups__organizations"

    def __str__(self):
        if hasattr(self, "user") and self.user is not None:
            return self.user.get_full_name()
        return self.display_name

    def __repr__(self) -> str:
        return f"<Researcher pk={self.pk} name={str(self)}>"

    @property
    def display_name(self):
        return f"{self.given_name.capitalize()} {self.family_name.capitalize()}"

    def get_owner(self):
        return self.user
