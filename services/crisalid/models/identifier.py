from django.db import models

# identifiers types from crisalid
# https://github.com/CRISalid-esr/crisalid-ikg/blob/dev-main/app/models/identifier_types.py


class OrganizationHarvester(models.TextChoices):
    """OrganizationIdentifierType (structures and authority organizations)"""

    IDREF = "idref"
    ROR = "ror"
    NNS = "nns"
    LOCAL = "local"
    UAI = "uai"
    SIREN = "siren"
    SIRET = "siret"
    WIKIDATA = "wikidata"
    SCOPUS = "scopus"
    HAL = "hal"
    OPENALEX = "openalex"
    ISNI = "isni"
    VIAF = "viaf"


class AbstractIdentifier(models.Model):
    """identifier owned by a crisalid object (from crisalid "identifiers")

    an identifier can be sent by several crisalid instances (configs): it is
    deleted when no config references it anymore
    """

    harvester = models.CharField(max_length=50)
    value = models.CharField(max_length=255)
    configs = models.ManyToManyField("crisalid.CrisalidConfig", blank=True)

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.harvester} :: {self.value}"

    def __repr__(self):
        return f"<{type(self).__name__} pk={self.pk} {str(self)}>"


class ResearcherIdentifier(AbstractIdentifier):
    class Harvester(models.TextChoices):
        """PersonIdentifierType"""

        ORCID = "orcid"
        IDREF = "idref"
        IDHALS = "idhals"
        IDHALI = "idhali"
        SCOPUS = "scopus"
        LOCAL = "local"
        EPPN = "eppn"

    researcher = models.ForeignKey(
        "crisalid.Researcher", on_delete=models.CASCADE, related_name="identifiers"
    )
    harvester = models.CharField(max_length=50, choices=Harvester.choices)

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=("researcher", "harvester", "value"),
                name="unique_researcher_identifier",
            ),
        )


class StructureIdentifier(AbstractIdentifier):
    Harvester = OrganizationHarvester

    structure = models.ForeignKey(
        "crisalid.Structure", on_delete=models.CASCADE, related_name="identifiers"
    )
    harvester = models.CharField(max_length=50, choices=Harvester.choices)

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=("structure", "harvester", "value"),
                name="unique_structure_identifier",
            ),
        )


class AuthorityOrganizationIdentifier(AbstractIdentifier):
    Harvester = OrganizationHarvester

    authority_organization = models.ForeignKey(
        "crisalid.AuthorityOrganization",
        on_delete=models.CASCADE,
        related_name="identifiers",
    )
    harvester = models.CharField(max_length=50, choices=Harvester.choices)

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=("authority_organization", "harvester", "value"),
                name="unique_authority_organization_identifier",
            ),
        )


class DocumentIdentifier(AbstractIdentifier):
    class Harvester(models.TextChoices):
        """documents are identified by their source records ("recorded_by")
        https://github.com/CRISalid-esr/crisalid-ikg/blob/dev-main/app/models/harvesters.py
        """

        HAL = "hal"
        SCANR = "scanr"
        IDREF = "idref"
        OPENALEX = "openalex"
        SCOPUS = "scopus"

    document = models.ForeignKey(
        "crisalid.Document", on_delete=models.CASCADE, related_name="identifiers"
    )
    harvester = models.CharField(max_length=50, choices=Harvester.choices)

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=("document", "harvester", "value"),
                name="unique_document_identifier",
            ),
        )


class JournalIdentifier(AbstractIdentifier):
    class Harvester(models.TextChoices):
        """JournalIdentifierType"""

        DOI = "doi"
        ISSN = "issn"

    journal = models.ForeignKey(
        "crisalid.Journal", on_delete=models.CASCADE, related_name="identifiers"
    )
    harvester = models.CharField(max_length=50, choices=Harvester.choices)

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=("journal", "harvester", "value"),
                name="unique_journal_identifier",
            ),
        )
