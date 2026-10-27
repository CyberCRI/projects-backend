from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.commons.mixins import TimestampedModelMixin


class AuthorityOrganization(TimestampedModelMixin):
    """Organization from documents affiliations in the Crisalid system"""

    class OrganizationType(models.TextChoices):
        """Authority organization type from crisalid (AuthorityOrganizationType)"""

        ORGANIZATION = "organization", _("Organization")
        INSTITUTION = "institution", _("Institution")
        INSTITUTION_GROUP = "institution_group", _("Institution group")
        LABORATORY = "laboratory", _("Laboratory")
        LABORATORY_GROUP = "laboratory_group", _("Laboratory group")
        RESEARCH_TEAM = "research_team", _("Research team")
        RESEARCH_TEAM_GROUP = "research_team_group", _("Research team group")

    crisalid_uid = models.CharField(max_length=255, unique=True)
    name = models.CharField(max_length=2048)
    type = models.CharField(  # noqa: A003
        max_length=50, choices=OrganizationType.choices, blank=True
    )
    identifiers = models.ManyToManyField(
        "crisalid.Identifier", related_name="authority_organizations"
    )

    def __str__(self):
        return self.name
