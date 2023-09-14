from typing import TYPE_CHECKING, List

from django.db import models

from apps.commons.db.abc import OrganizationRelated

if TYPE_CHECKING:
    from apps.organizations.models import Organization


class Language(models.TextChoices):
    """
    Represent a language, e.g: fr
    """

    FR = "fr", "French"
    EN = "en", "English"

    @classmethod
    def default(cls):
        return Language.EN


class SDG(models.IntegerChoices):
    """
    Represent an SDG by its number.
    See https://www.un.org/sustainabledevelopment
    """

    NO_POVERTY = 1, "No poverty"
    ZERO_HUNGER = 2, "Zero hunger"
    GOOD_HEALTH_AND_WELL_BEING = 3, "Good health and well-being"
    QUALITY_EDUCATION = 4, "Quality education"
    GENDER_EQUALITY = 5, "Gender equality"
    CLEAN_WATER_AND_SANITATION = 6, "Clean water and sanitation"
    AFFORDABLE_AND_CLEAN_ENERGY = 7, "Affordable and clean energy"
    DECENT_WORK_AND_ECONOMIC_GROWTH = 8, "Decent work and economic growth"
    INDUSTRY_INNOVATION_AND_INFRASTRUCTURE = (
        9,
        "Industry, innovation and infrastructure",
    )
    REDUCED_INEQUALITIES = 10, "Reduces inequalities"
    SUSTAINABLE_CITIES_AND_COMMUNITIES = 11, "Sustainable cities and communities"
    RESPONSIBLE_CONSUMPTION_AND_PRODUCTION = 12, "Responsible consumption & production"
    CLIMATE_ACTION = 13, "Climate action"
    LIFE_BELOW_WATER = 14, "Life below water"
    LIFE_ON_LAND = 15, "Life on land"
    PEACE_JUSTICE_AND_STRONG_INSTITUTIONS = 16, "Peace, justice and strong institutions"
    PARTNERSHIPS_FOR_THE_GOALS = 17, "Partnerships for the goals"


class WikipediaTag(models.Model):
    name = models.CharField(max_length=255, help_text="name of the tag")
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
