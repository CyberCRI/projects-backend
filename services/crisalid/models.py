"""
Il faut qu’on crée les correspondances entre nos schémas et ceux de la base Neo4j.
Il y a 3 types de données qu’on veut importer avec les liens qui peuvent exister entre elles :
    - Institutions et structures de recherche
    - Documents (thèses, livres, rapports, etc.)
    - Personnes
        Les personnes ont plusieurs identifiants, plusieurs noms (prise en compte des changements de nom, marriage, etc.).
        Elles ont un lien aux documents en fonction de leur contribution. Ces liens peuvent prendre des formes différents.
        Elles ont des liens aux institutions (type employment) et aux structures de recherche (type membership).
        Ces liens ne veulent pas dire la même chose. On peut faire partie d’une structure de recherche sans être lié par un contrat de travail.
"""

from django.contrib.contenttypes.models import ContentType
from django.db import models


class CrisalidId(models.Model):
    """
    Represents a unique identifier for a Crisalid entity.
    """

    class IDType(models.TextChoices):
        ORCID = "ORCID"
        CRISALID = "CRISALID"

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    id_type = models.CharField(max_length=50, choices=IDType.choices)
    value = models.CharField(max_length=255)

    class Meta:
        unique_together = ("content_type", "id_type", "value")


class CrisalidDataModel(models.Model):
    crisalid_ids = models.ManyToManyField(
        "crisalid.CrisalidId",
        related_name="researchers",
        blank=True,
    )

    class Meta:
        abstract = True


class Researcher(CrisalidDataModel):
    user = models.ForeignKey(
        "accounts.ProjectUser",
        on_delete=models.CASCADE,
        related_name="researchers",
    )
    employments = models.ManyToManyField(
        "crisalid.ResearchEmployment",
        related_name="researchers",
        through="crisalid.ResearchEmployment",
        blank=True,
    )
    memberships = models.ManyToManyField(
        "crisalid.ResearchMembership",
        related_name="researchers",
        through="crisalid.ResearchMembership",
        blank=True,
    )
    documents = models.ManyToManyField(
        "crisalid.ResearchDocument",
        related_name="authors",
        blank=True,
    )


class ResearchInstitution(CrisalidDataModel):
    """
    Represents an institution in the Crisalid system.
    """
    name = models.CharField(max_length=255)


class ResearchTeam(CrisalidDataModel):
    """
    Represents a research team in the Crisalid system.
    """
    name = models.CharField(max_length=255)
    institutions = models.ManyToManyField(
        "crisalid.ResearchInstitution",
        related_name="teams",
        blank=True,
    )


class ResearchDocument(CrisalidDataModel):
    """
    Represents a research document in the Crisalid system.
    """

    class DocumentType(models.TextChoices):
        THESIS = "THESIS"
        BOOK = "BOOK"
        REPORT = "REPORT"
        ARTICLE = "ARTICLE"

    type = models.CharField(max_length=50, choices=DocumentType.choices)
    title = models.CharField(max_length=255)
    link = models.URLField(blank=True, null=True)
    publication_date = models.DateField(blank=True, null=True)


class ResearchEmployment(CrisalidDataModel):
    """
    Represents an employment relationship between a researcher and an institution.
    """
    researcher = models.ForeignKey(
        "crisalid.Researcher",
        on_delete=models.CASCADE,
        related_name="employments",
    )
    institution = models.ForeignKey(
        "crisalid.ResearchInstitution",
        on_delete=models.CASCADE,
        related_name="employments",
    )
    role = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)


class ResearchMembership(CrisalidDataModel):
    """
    Represents a membership relationship between a researcher and a research team.
    """
    researcher = models.ForeignKey(
        "crisalid.Researcher",
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    team = models.ForeignKey(
        "crisalid.ResearchTeam",
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    role = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
