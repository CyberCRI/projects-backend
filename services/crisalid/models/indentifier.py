from django.db import models
from django.db.models.functions import Lower


class Identifier(models.Model):
    class Harvester(models.TextChoices):
        """Harvester from crisalid (where the source comme from)
        src: https://www.esup-portail.org/wiki/spaces/ESUPCRISalid/pages/1674084377/Normalisation+des+identifiants
        """

        ORCID = "orcid"
        IDREF = "idref"
        HAL = "hal"
        IDHALS = "idhals"
        IDHALI = "idhali"
        SCOPUS = "scopus"
        SCANR = "scanr"
        OPENALEX = "openalex"
        SCIENCEPLUS = "scienceplus"
        SUDOC = "sudoc"
        OPENEDITION = "openedition"
        PERSEE = "persee"
        LOCAL = "local"
        EPPN = "eppn"
        ROR = "ror"
        NNS = "nns"
        UAI = "uai"
        SIREN = "siren"
        SIRET = "siret"
        GRID = "grid"
        WIKIDATA = "wikidata"
        FUNDREF = "fundref"
        ISNI = "isni"
        GOOGLESCHOLAR = "googlescholar"
        VIAF = "viaf"
        DOI = "doi"
        ISSN = "issn"
        ARXIV = "arxiv"
        BIBCODE = "bibcode"
        BIORXIV = "biorxiv"
        CERN = "cern"
        CHEMRXIV = "chemrxiv"
        ENSAM = "ensam"
        INERIS = "ineris"
        INSPIRE = "inspire"
        IRD = "ird"
        IRSTEA = "irstea"
        MEDITAGRI = "meditagri"
        NNT = "nnt"
        OKINA = "okina"
        OATAO = "oatao"
        PII = "pii"
        PMID = "pmid"
        PMCID = "pmcid"
        PPN = "ppn"
        PRODINRA = "prodinra"
        SCIENCESPO = "sciencespo"
        SWHID = "swhid"
        URI = "uri"
        WOS = "wos"

    harvester = models.CharField(max_length=50, choices=Harvester.choices)
    value = models.CharField(max_length=255)

    class Meta:
        constraints = (
            # we cant have the same harvester and value
            models.UniqueConstraint(
                Lower("harvester"),
                Lower("value"),
                name="unique_harvester",
                condition=~models.Q(harvester="local"),
            ),
        )

    def __str__(self):
        return f"{self.harvester} :: {self.value}"

    def __repr__(self):
        return f"<Identifier {str(self)} >"
