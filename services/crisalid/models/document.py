from collections.abc import Generator

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.commons.fields import ChoiceArrayField
from apps.commons.mixins import (
    HasEmbedding,
    HasRelatedModules,
    OrganizationRelated,
    TimestampedModelMixin,
)
from apps.organizations.models import Organization
from apps.skills.models import Tag
from services.crisalid.manager import DocumentQuerySet
from services.crisalid.relators import RolesChoices
from services.translator.mixins import HasAutoTranslatedFields


class DocumentContributor(models.Model):
    """
    models to add which role researcher have in document
    """

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

    def __str__(self):
        return f"document={self.document_id} researcher={self.researcher_id} roles={self.roles!r}"


class DocumentDomains(models.Model):
    """
    models to add domain to a document
    """

    domain = models.ForeignKey(Tag, on_delete=models.CASCADE)
    document = models.ForeignKey(
        "crisalid.Document",
        on_delete=models.CASCADE,
        related_name="document_domains",
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
                "document",
                name="unique_domain_document",
            ),
        )

    def __str__(self) -> str:
        return f"{self.domain} level={self.level}"


class DocumentJournal(models.Model):
    """model through from document to a journal (https://github.com/CRISalid-esr/crisalid-ikg/blob/dev-main/app/models/document_publication_channel.py#L6)"""

    document = models.ForeignKey(
        "crisalid.Document",
        on_delete=models.CASCADE,
        related_name="document_journals",
    )
    journal = models.ForeignKey(
        "crisalid.Journal", on_delete=models.CASCADE, related_name="document_journals"
    )

    pages = models.CharField(blank=True, null=True, default="")
    volume = models.CharField(blank=True, null=True, default="")
    issue = models.CharField(blank=True, null=True, default="")

    def __str__(self):
        return f"{self.journal} {self.document}"


class Document(
    HasRelatedModules,
    TimestampedModelMixin,
    HasEmbedding,
    OrganizationRelated,
    HasAutoTranslatedFields,
):
    """
    Represents a research publicaiton (or 'document') in the Crisalid system.
    """

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

    domains = models.ManyToManyField(
        Tag, through=DocumentDomains, related_name="documents"
    )

    journals = models.ManyToManyField(
        "crisalid.Journal", through=DocumentJournal, related_name="documents"
    )

    organization_query_string = "contributors__user__groups__organizations"

    objects = DocumentQuerySet.as_manager()

    class Meta:
        # order by publicattion date, and put "null date" at last
        ordering = (models.F("publication_date").desc(nulls_last=True),)

    def __str__(self):
        return f"<{self.document_type}> {self.title}"

    def save(self, *ar, **kw):
        md = super().save(*ar, **kw)
        # when we update models , re-calculate vectorize
        self.vectorize()
        return md

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
    def document_type_centralized(self) -> tuple[str]:
        """get group list document centralized"""
        for vals in DocumentTypeCentralized.values():
            if self.document_type in vals:
                return vals
        return (self.document_type,)


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
