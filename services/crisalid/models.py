from django.db import models
from django.db.models.functions import Lower


class CrisalidDataModel(models.Model):
    crisalid_uid = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        abstract = True
        constraints = (
            models.UniqueConstraint(
                "crisalid_uid", name="%(app_label)s_%(class)s_unique_crisalid_uid"
            ),
        )


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

    harvester = models.CharField(max_length=50, choices=Harvester.choices)
    value = models.CharField(max_length=255)

    class Meta:
        constraints = (
            # we cant have the same harvester, docuement type linked to a document
            models.UniqueConstraint(
                Lower("harvester"), Lower("value"), name="unique_harvester"
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
    display_name = models.CharField(max_length=200, blank=True, null=True)
    identifiers = models.ManyToManyField(
        "crisalid.Identifier", related_name="researchers"
    )

    def __str__(self):
        if hasattr(self, "user") and self.user is not None:
            return self.user.get_full_name()
        return f"{self.display_name}"


class Document(CrisalidDataModel):
    """
    Represents a research document in the Crisalid system.
    """

    title = models.TextField()
    publication_date = models.DateField(blank=False, null=True)
    authors = models.ManyToManyField("crisalid.Researcher", related_name="documents")


class DocumentSource(CrisalidDataModel):
    """Represents the data source/link of a document/publications"""

    class DocumentType(models.TextChoices):
        """
        Document type from crisalid
        https://github.com/CRISalid-esr/crisalid-ikg/blob/dev-main/app/models/document_type.py#L9
        """

        AUDIOVISUAL_DOCUMENT = "Audiovisual Document"
        BLOG_POST = "Blog Post"
        BOOK = "Book"
        BOOK_REVIEW = "Book Review"
        CHAPTER = "Chapter"
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

    document_type = models.CharField(
        max_length=50, choices=DocumentType.choices, null=True, blank=True
    )
    value = models.TextField()
    identifier = models.ForeignKey(
        "crisalid.Identifier", on_delete=models.CASCADE, related_name="documents"
    )
    document = models.ForeignKey(
        "crisalid.Document", on_delete=models.CASCADE, related_name="sources"
    )

    class Meta:
        constraints = (
            # we cant have the same identifier, docuement type linked to a document
            models.UniqueConstraint(
                "identifier",
                "document",
                "document_type",
                name="unique_document_identifier",
            ),
        )
