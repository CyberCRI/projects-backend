from collections.abc import Generator

from django import forms
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models.functions import Lower
from django.utils.translation import gettext_lazy as _

from apps.commons.mixins import HasEmbedding, OrganizationRelated
from apps.organizations.models import Organization
from services.crisalid.relators import RolesChoices
from services.translator.mixins import HasAutoTranslatedFields

from .manager import CrisalidQuerySet, DocumentQuerySet


class ChoiceArrayField(ArrayField):
    """
    A field that allows us to store an array of choices.
    Uses Django's Postgres ArrayField
    and a MultipleChoiceField for its formfield.
    https://gist.github.com/danni/f55c4ce19598b2b345ef
    """

    class TypedMultipleChoiceField(forms.TypedMultipleChoiceField):
        def __init__(self, *args, **kwargs):
            kwargs.pop("base_field", None)
            kwargs.pop("max_length", None)
            super().__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        defaults = {
            "form_class": ChoiceArrayField.TypedMultipleChoiceField,
            "choices": self.base_field.choices,
            "coerce": self.base_field.to_python,
        } | kwargs
        return super(ArrayField, self).formfield(**defaults)


class CrisalidDataModel(models.Model):
    updated = models.DateTimeField(auto_created=True, auto_now=True)

    class Meta:
        abstract = True


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


class Researcher(CrisalidDataModel):
    """Link to a crisalid"""

    PRIVACY_HARVESTER = (
        Identifier.Harvester.EPPN,
        Identifier.Harvester.PPN,
        Identifier.Harvester.LOCAL,
    )

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

    objects = CrisalidQuerySet.as_manager()

    def __str__(self):
        if hasattr(self, "user") and self.user is not None:
            return self.user.get_full_name()
        return self.display_name

    @property
    def display_name(self):
        return f"{self.given_name.capitalize()} {self.family_name.capitalize()}"


class DocumentContributor(models.Model):
    roles = ChoiceArrayField(
        models.CharField(max_length=255, choices=RolesChoices), default=list
    )
    document = models.ForeignKey("crisalid.Document", on_delete=models.CASCADE)
    researcher = models.ForeignKey("crisalid.Researcher", on_delete=models.CASCADE)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["document", "researcher"],
                name="unique_researcher_document",
            )
        ]


class Document(
    HasEmbedding,
    OrganizationRelated,
    HasAutoTranslatedFields,
    CrisalidDataModel,
):
    """
    Represents a research publicaiton (or 'document') in the Crisalid system.
    """

    objects = DocumentQuerySet.as_manager()

    class DocumentType(models.TextChoices):
        """
        Document type from crisalid
        https://www.esup-portail.org/wiki/spaces/ESUPCRISalid/pages/1418985474/Typologie+g%C3%A9n%C3%A9rale+des+documents
        https://github.com/CRISalid-esr/crisalid-ikg/blob/dev-main/app/graph/neo4j/document_dao.py#L40
        """

        DOCUMENT = "Document", _("Document")
        SCHOLARLYPUBLICATION = "ScholarlyPublication", _("Scholarly Publication")
        ARTICLE = "Article", _("Article")
        JOURNALARTICLE = "JournalArticle", _("Journal Article")
        CONFERENCEARTICLE = "ConferenceArticle", _("Conference Article")
        CONFERENCEABSTRACT = "ConferenceAbstract", _("Conference Abstract")
        PREFACE = "Preface", _("Preface")
        COMMENT = "Comment", _("Comment")
        BOOKCHAPTER = "BookChapter", _("Book Chapter")
        BOOK = "Book", _("Book")
        MONOGRAPH = "Monograph", _("Monograph")
        PROCEEDINGS = "Proceedings", _("Proceedings")
        BOOKOFCHAPTERS = "BookOfChapters", _("Book Of Chapters")
        PRESENTATION = "Presentation", _("Presentation")
        UNKNOWN = "UNKNOWN", _("Unknown")

    auto_translated_fields = ["title", "description"]

    title = models.TextField()
    description = models.TextField(default="")
    publication_date = models.DateField(blank=False, null=True)
    document_type = models.CharField(
        max_length=50,
        choices=DocumentType.choices,
        default=DocumentType.UNKNOWN.value,
    )
    contributors = models.ManyToManyField(
        "crisalid.Researcher",
        through="crisalid.DocumentContributor",
        related_name="documents",
    )
    identifiers = models.ManyToManyField(
        "crisalid.Identifier", related_name="documents"
    )

    organization_query_string = "contributors__user__groups__organizations"

    class Meta:
        # order by publicattion date, and put "null date" at last
        ordering = (models.F("publication_date").desc(nulls_last=True),)

    def get_related_organizations(self):
        """organizations from user"""
        return list(
            Organization.objects.filter(
                id__in=self.contributors.all()
                .values_list("user__groups__organizations", flat=True)
                .distinct("id")
            )
        )

    def __str__(self):
        return f"<{self.document_type}> {self.title}"

    @property
    def document_type_centralized(self) -> list[str]:
        """get group list document centralized"""
        for vals in DocumentTypeCentralized.values():
            if self.document_type in vals:
                return vals
        return [self.document_type]

    def save(self, *ar, **kw):
        md = super().save(*ar, **kw)
        # when we update models , re-calculate vectorize
        self.vectorize()
        return md


class DocumentTypeCentralized:
    """this class centralized all document type to one type"""

    publications = (
        Document.DocumentType.ARTICLE.value,
        Document.DocumentType.DOCUMENT.value,
        Document.DocumentType.SCHOLARLYPUBLICATION.value,
        Document.DocumentType.ARTICLE.value,
        Document.DocumentType.JOURNALARTICLE.value,
        Document.DocumentType.BOOKCHAPTER.value,
        Document.DocumentType.BOOK.value,
    )
    conferences = (
        Document.DocumentType.CONFERENCEABSTRACT.value,
        Document.DocumentType.CONFERENCEARTICLE.value,
        Document.DocumentType.PRESENTATION.value,
    )

    @classmethod
    def items(cls) -> Generator[tuple[str, tuple[str]]]:
        for v in dir(cls):
            if not v.startswith("_") and isinstance(getattr(cls, v), (list, tuple)):
                yield v, getattr(cls, v)

    @classmethod
    def keys(cls) -> Generator[list[str]]:
        for k, _ in cls.items():  # noqa: F402
            yield k

    @classmethod
    def values(cls) -> Generator[tuple[str]]:
        for _, v in cls.items():  # noqa: F402
            yield v


class CrisalidConfig(OrganizationRelated, models.Model):
    """model for crisalid config with host/pass for connected to crisalid,
    is linked to a one organization
    """

    organization = models.OneToOneField(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="crisalid",
    )

    crisalidbus_url = models.CharField(
        max_length=255, help_text="crisalidbus/rabimqt host:port"
    )
    crisalidbus_username = models.CharField(
        max_length=255, help_text="crisalidbus/rabimqt username"
    )
    crisalidbus_password = models.CharField(
        max_length=255, help_text="crisalidbus/rabimqt password"
    )

    apollo_url = models.CharField(
        max_length=255, help_text="apollo/graphql host:port/graphql"
    )
    apollo_token = models.CharField(max_length=255, help_text="apollo token")

    active = models.BooleanField(help_text="config is enabled/disabled", default=False)

    def __str__(self):
        active = self.active
        return f"Config: {self.organization} ({active=})"
