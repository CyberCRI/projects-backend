from collections.abc import Generator

from django import forms
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models.functions import Lower

from apps.commons.mixins import HasEmbending, OrganizationRelated
from apps.organizations.models import Organization
from services.crisalid import relators
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
        """Harvester from crisalid (where the source comme from)"""

        HAL = "hal"
        SCANR = "scanr"
        OPENALEX = "openalex"
        IDREF = "idref"
        SCOPUS = "scopus"
        ORCID = "orcid"
        LOCAL = "local"
        EPPN = "eppn"
        DOI = "doi"
        PMID = "pmid"
        NNS = "nns"
        RNSR = "rnsr"

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
    memberships = models.ManyToManyField(
        "crisalid.Structure", related_name="memberships"
    )
    employments = models.ManyToManyField(
        "crisalid.Structure", related_name="employments"
    )

    def __str__(self):
        if hasattr(self, "user") and self.user is not None:
            return self.user.get_full_name()
        return self.display_name

    @property
    def display_name(self):
        return f"{self.given_name.capitalize()} {self.family_name.capitalize()}"


class DocumentContributor(models.Model):
    roles = ChoiceArrayField(
        models.CharField(max_length=255, choices=relators.choices), default=list
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
    HasEmbending, OrganizationRelated, HasAutoTranslatedFields, CrisalidDataModel
):
    """
    Represents a research publicaiton (or 'document') in the Crisalid system.
    """

    objects = DocumentQuerySet.as_manager()

    class DocumentType(models.TextChoices):
        """
        Document type from crisalid
        https://github.com/CRISalid-esr/crisalid-ikg/blob/dev-main/app/models/document_type.py#L9
        """

        AUDIOVISUAL_DOCUMENT = "Audiovisual Document"
        BLOG_POST = "Blog Post"
        BOOK = "Book"
        BOOK_REVIEW = "Book Review"
        BOOKCHAPTER = "BookChapter"
        CHAPTER = "Chapter"
        ConferenceArticle = "ConferenceArticle"
        CONFERENCE_OUTPUT = "Conference Output"
        CONFERENCE_PAPER = "Conference Paper"
        CONFERENCE_POSTER = "Conference Poster"
        DATA_MANAGEMENT_PLAN = "Data Management Plan"
        DATA_PAPER = "Data Paper"
        DATASET = "Dataset"
        DICTIONARY = "Reference Book"
        DOCUMENT = "Document"
        EDITORIAL = "Editorial"
        ERRATUM = "Erratum"
        GRANT = "Grant"
        IMAGE = "Image"
        JOURNALARTICLE = "JournalArticle"
        LECTURE = "Lecture"
        LETTER = "Letter"
        MANUAL = "Manual"
        MAP = "Map"
        MASTER_THESIS = "Master Thesis"
        METADATA_DOCUMENT = "Metadata Document"
        NOTE = "Note"
        OTHER = "Other"
        PATENT = "Patent"
        PEER_REVIEW = "Peer review"
        PREPRINT = "Preprint"
        PROCEEDINGS = "Proceedings"
        REPORT = "Report"
        RESEARCH_REPORT = "Research Report"
        REVIEW = "Review Paper"
        REVIEW_ARTICLE = "Review Article"
        SOFTWARE = "Software"
        STANDARD = "Standard"
        STILL_IMAGE = "Still Image"
        TECHNICAL_REPORT = "Technical Report"
        THESIS = "Thesis"
        WORKING_PAPER = "Working Paper"
        UNKNOWN = "Unknown"

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
        Document.DocumentType.JOURNALARTICLE.value,
        Document.DocumentType.AUDIOVISUAL_DOCUMENT.value,
        Document.DocumentType.BLOG_POST.value,
        Document.DocumentType.BOOK.value,
        Document.DocumentType.BOOK_REVIEW.value,
        Document.DocumentType.BOOKCHAPTER.value,
        Document.DocumentType.CHAPTER.value,
        Document.DocumentType.DICTIONARY.value,
        Document.DocumentType.DOCUMENT.value,
        Document.DocumentType.EDITORIAL.value,
        Document.DocumentType.LETTER.value,
        Document.DocumentType.MANUAL.value,
        Document.DocumentType.REVIEW_ARTICLE.value,
        Document.DocumentType.THESIS.value,
    )
    conferences = (
        Document.DocumentType.ConferenceArticle.value,
        Document.DocumentType.CONFERENCE_OUTPUT.value,
        Document.DocumentType.CONFERENCE_PAPER.value,
        Document.DocumentType.CONFERENCE_POSTER.value,
    )

    @classmethod
    def items(cls) -> Generator[tuple[str, tuple[str]]]:
        for v in dir(cls):
            if not v.startswith("_") and isinstance(getattr(cls, v), (list, tuple)):
                yield v, getattr(cls, v)

    @classmethod
    def keys(cls) -> Generator[list[str]]:
        for k, _ in cls.items():
            yield k

    @classmethod
    def values(cls) -> Generator[tuple[str]]:
        for _, v in cls.items():
            yield v


class Structure(OrganizationRelated, CrisalidDataModel):
    acronym = models.TextField(null=True, blank=True)
    name = models.TextField()
    identifiers = models.ManyToManyField(
        "crisalid.Identifier", related_name="structures"
    )
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="structures",
    )
    objects = CrisalidQuerySet.as_manager()
    group = models.ForeignKey(
        "accounts.PeopleGroup",
        on_delete=models.SET_NULL,
        null=True,
        related_name="structure",
    )

    def __str__(self):
        return self.name


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
