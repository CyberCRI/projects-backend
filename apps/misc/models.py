from typing import TYPE_CHECKING, List

from django.db import models

from apps.commons.models import OrganizationRelated

if TYPE_CHECKING:
    from apps.organizations.models import Organization


class WikipediaTag(models.Model):
    name = models.CharField(max_length=255, help_text="name of the tag")
    description = models.CharField(max_length=255, blank=True)
    wikipedia_qid = models.CharField(
        max_length=50,
        unique=True,
        help_text="Wikidata item ID, e.g https://www.wikidata.org/wiki/Q1 is Q1",
    )

    def __str__(self):
        return str(self.name)


class Tag(models.Model, OrganizationRelated):
    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=255)

    def __str__(self) -> str:
        return self.name

    def get_related_organizations(self) -> List["Organization"]:
        """Return the organizations related to this model."""
        return [self.organization]
