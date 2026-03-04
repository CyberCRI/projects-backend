from collections.abc import Generator

from django import forms
from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models.functions import Lower
from django.utils.translation import gettext_lazy as _

from apps.commons.mixins import HasEmbedding, OrganizationRelated
from apps.organizations.models import Organization
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
    class RolesChoices(models.TextChoices):
        """
        values from https://id.loc.gov/vocabulary/relators.json
        """

        ABR = "ABR", _("abridger")
        ACP = "ACP", _("art copyist")
        ACT = "ACT", _("actor")
        ADI = "ADI", _("art director")
        ADP = "ADP", _("adapter")
        AFT = "AFT", _("author of afterword, colophon, etc.")
        ANC = "ANC", _("announcer")
        ANL = "ANL", _("analyst")
        ANM = "ANM", _("animator")
        ANN = "ANN", _("annotator")
        ANT = "ANT", _("bibliographic antecedent")
        APE = "APE", _("appellee")
        APL = "APL", _("appellant")
        APP = "APP", _("applicant")
        AQT = "AQT", _("author in quotations or text abstracts")
        ARC = "ARC", _("architect")
        ARD = "ARD", _("artistic director")
        ARR = "ARR", _("arranger")
        ART = "ART", _("artist")
        ASG = "ASG", _("assignee")
        ASN = "ASN", _("associated name")
        ATO = "ATO", _("autographer")
        ATT = "ATT", _("attributed name")
        AUC = "AUC", _("auctioneer")
        AUD = "AUD", _("author of dialog")
        AUE = "AUE", _("audio engineer")
        AUI = "AUI", _("author of introduction, etc.")
        AUP = "AUP", _("audio producer")
        AUS = "AUS", _("screenwriter")
        AUT = "AUT", _("author")
        BDD = "BDD", _("binding designer")
        BJD = "BJD", _("bookjacket designer")
        BKA = "BKA", _("book artist")
        BKD = "BKD", _("book designer")
        BKP = "BKP", _("book producer")
        BLW = "BLW", _("blurb writer")
        BND = "BND", _("binder")
        BPD = "BPD", _("bookplate designer")
        BRD = "BRD", _("broadcaster")
        BRL = "BRL", _("braille embosser")
        BSL = "BSL", _("bookseller")
        CAD = "CAD", _("casting director")
        CAS = "CAS", _("caster")
        CCP = "CCP", _("conceptor")
        CHR = "CHR", _("choreographer")
        CLI = "CLI", _("client")
        CLL = "CLL", _("calligrapher")
        CLR = "CLR", _("colorist")
        CLT = "CLT", _("collotyper")
        CMM = "CMM", _("commentator")
        CMP = "CMP", _("composer")
        CMT = "CMT", _("compositor")
        CND = "CND", _("conductor")
        CNG = "CNG", _("cinematographer")
        CNS = "CNS", _("censor")
        COE = "COE", _("contestant-appellee")
        COL = "COL", _("collector")
        COM = "COM", _("compiler")
        CON = "CON", _("conservator")
        COP = "COP", _("camera operator")
        COR = "COR", _("collection registrar")
        COS = "COS", _("contestant")
        COT = "COT", _("contestant-appellant")
        COU = "COU", _("court governed")
        COV = "COV", _("cover designer")
        CPC = "CPC", _("copyright claimant")
        CPE = "CPE", _("complainant-appellee")
        CPH = "CPH", _("copyright holder")
        CPL = "CPL", _("complainant")
        CPT = "CPT", _("complainant-appellant")
        CRE = "CRE", _("creator")
        CRP = "CRP", _("correspondent")
        CRR = "CRR", _("corrector")
        CRT = "CRT", _("court reporter")
        CSL = "CSL", _("consultant")
        CSP = "CSP", _("consultant to a project")
        CST = "CST", _("costume designer")
        CTB = "CTB", _("contributor")
        CTE = "CTE", _("contestee-appellee")
        CTG = "CTG", _("cartographer")
        CTR = "CTR", _("contractor")
        CTS = "CTS", _("contestee")
        CTT = "CTT", _("contestee-appellant")
        CUR = "CUR", _("curator")
        CWT = "CWT", _("commentator for written text")
        DBD = "DBD", _("dubbing director")
        DBP = "DBP", _("distribution place")
        DFD = "DFD", _("defendant")
        DFE = "DFE", _("defendant-appellee")
        DFT = "DFT", _("defendant-appellant")
        DGC = "DGC", _("degree committee member")
        DGG = "DGG", _("degree granting institution")
        DGS = "DGS", _("degree supervisor")
        DIS = "DIS", _("dissertant")
        DJO = "DJO", _("dj")
        DLN = "DLN", _("delineator")
        DNC = "DNC", _("dancer")
        DNR = "DNR", _("donor")
        DPC = "DPC", _("depicted")
        DPT = "DPT", _("depositor")
        DRM = "DRM", _("draftsman")
        DRT = "DRT", _("director")
        DSR = "DSR", _("designer")
        DST = "DST", _("distributor")
        DTC = "DTC", _("data contributor")
        DTE = "DTE", _("dedicatee")
        DTM = "DTM", _("data manager")
        DTO = "DTO", _("dedicator")
        DUB = "DUB", _("dubious author")
        EDC = "EDC", _("editor of compilation")
        EDD = "EDD", _("editorial director")
        EDM = "EDM", _("editor of moving image work")
        EDT = "EDT", _("editor")
        EGR = "EGR", _("engraver")
        ELG = "ELG", _("electrician")
        ELT = "ELT", _("electrotyper")
        ENG = "ENG", _("engineer")
        ENJ = "ENJ", _("enacting jurisdiction")
        ETR = "ETR", _("etcher")
        EVP = "EVP", _("event place")
        EXP = "EXP", _("expert")
        FAC = "FAC", _("facsimilist")
        FDS = "FDS", _("film distributor")
        FLD = "FLD", _("field director")
        FLM = "FLM", _("film editor")
        FMD = "FMD", _("film director")
        FMK = "FMK", _("filmmaker")
        FMO = "FMO", _("former owner")
        FMP = "FMP", _("film producer")
        FND = "FND", _("funder")
        FON = "FON", _("founder")
        FPY = "FPY", _("first party")
        FRG = "FRG", _("forger")
        GDV = "GDV", _("game developer")
        GIS = "GIS", _("geographic information specialist")
        HIS = "HIS", _("host institution")
        HNR = "HNR", _("honoree")
        HST = "HST", _("host")
        ILL = "ILL", _("illustrator")
        ILU = "ILU", _("illuminator")
        INK = "INK", _("inker")
        INS = "INS", _("inscriber")
        INV = "INV", _("inventor")
        ISB = "ISB", _("issuing body")
        ITR = "ITR", _("instrumentalist")
        IVE = "IVE", _("interviewee")
        IVR = "IVR", _("interviewer")
        JUD = "JUD", _("judge")
        JUG = "JUG", _("jurisdiction governed")
        LBR = "LBR", _("laboratory")
        LBT = "LBT", _("librettist")
        LDR = "LDR", _("laboratory director")
        LED = "LED", _("lead")
        LEE = "LEE", _("libelee-appellee")
        LEL = "LEL", _("libelee")
        LEN = "LEN", _("lender")
        LET = "LET", _("libelee-appellant")
        LGD = "LGD", _("lighting designer")
        LIE = "LIE", _("libelant-appellee")
        LIL = "LIL", _("libelant")
        LIT = "LIT", _("libelant-appellant")
        LSA = "LSA", _("landscape architect")
        LSE = "LSE", _("licensee")
        LSO = "LSO", _("licensor")
        LTG = "LTG", _("lithographer")
        LTR = "LTR", _("letterer")
        LYR = "LYR", _("lyricist")
        MCP = "MCP", _("music copyist")
        MDC = "MDC", _("metadata contact")
        MED = "MED", _("medium")
        MFP = "MFP", _("manufacture place")
        MFR = "MFR", _("manufacturer")
        MKA = "MKA", _("makeup artist")
        MOD = "MOD", _("moderator")
        MON = "MON", _("monitor")
        MRB = "MRB", _("marbler")
        MRK = "MRK", _("markup editor")
        MSD = "MSD", _("musical director")
        MTE = "MTE", _("metal engraver")
        MTK = "MTK", _("minute taker")
        MUP = "MUP", _("music programmer")
        MUS = "MUS", _("musician")
        MXE = "MXE", _("mixing engineer")
        NAN = "NAN", _("news anchor")
        NRT = "NRT", _("narrator")
        ONP = "ONP", _("onscreen participant")
        OPN = "OPN", _("opponent")
        ORG = "ORG", _("originator")
        ORM = "ORM", _("organizer")
        OSP = "OSP", _("onscreen presenter")
        OTH = "OTH", _("other")
        OWN = "OWN", _("owner")
        PAD = "PAD", _("place of address")
        PAN = "PAN", _("panelist")
        PAT = "PAT", _("patron")
        PBD = "PBD", _("publisher director")
        PBL = "PBL", _("publisher")
        PDR = "PDR", _("project director")
        PFR = "PFR", _("proofreader")
        PHT = "PHT", _("photographer")
        PLT = "PLT", _("platemaker")
        PMA = "PMA", _("permitting agency")
        PMN = "PMN", _("production manager")
        PNC = "PNC", _("penciller")
        POP = "POP", _("printer of plates")
        PPM = "PPM", _("papermaker")
        PPT = "PPT", _("puppeteer")
        PRA = "PRA", _("praeses")
        PRC = "PRC", _("process contact")
        PRD = "PRD", _("production personnel")
        PRE = "PRE", _("presenter")
        PRF = "PRF", _("performer")
        PRG = "PRG", _("programmer")
        PRM = "PRM", _("printmaker")
        PRN = "PRN", _("production company")
        PRO = "PRO", _("producer")
        PRP = "PRP", _("production place")
        PRS = "PRS", _("production designer")
        PRT = "PRT", _("printer")
        PRV = "PRV", _("provider")
        PTA = "PTA", _("patent applicant")
        PTE = "PTE", _("plaintiff-appellee")
        PTF = "PTF", _("plaintiff")
        PTH = "PTH", _("patent holder")
        PTT = "PTT", _("plaintiff-appellant")
        PUP = "PUP", _("publication place")
        RAP = "RAP", _("rapporteur")
        RBR = "RBR", _("rubricator")
        RCD = "RCD", _("recordist")
        RCE = "RCE", _("recording engineer")
        RCP = "RCP", _("addressee")
        RDD = "RDD", _("radio director")
        RED = "RED", _("redaktor")
        REN = "REN", _("renderer")
        RES = "RES", _("researcher")
        REV = "REV", _("reviewer")
        RPC = "RPC", _("radio producer")
        RPS = "RPS", _("repository")
        RPT = "RPT", _("reporter")
        RPY = "RPY", _("responsible party")
        RSE = "RSE", _("respondent-appellee")
        RSG = "RSG", _("restager")
        RSP = "RSP", _("respondent")
        RSR = "RSR", _("restorationist")
        RST = "RST", _("respondent-appellant")
        RTH = "RTH", _("research team head")
        RTM = "RTM", _("research team member")
        RXA = "RXA", _("remix artist")
        SAD = "SAD", _("scientific advisor")
        SCE = "SCE", _("scenarist")
        SCL = "SCL", _("sculptor")
        SCR = "SCR", _("scribe")
        SDE = "SDE", _("sound engineer")
        SDS = "SDS", _("sound designer")
        SEC = "SEC", _("secretary")
        SFX = "SFX", _("special effects provider")
        SGD = "SGD", _("stage director")
        SGN = "SGN", _("signer")
        SHT = "SHT", _("supporting host")
        SLL = "SLL", _("seller")
        SNG = "SNG", _("singer")
        SPK = "SPK", _("speaker")
        SPN = "SPN", _("sponsor")
        SPY = "SPY", _("second party")
        SRV = "SRV", _("surveyor")
        STD = "STD", _("set designer")
        STG = "STG", _("setting")
        STL = "STL", _("storyteller")
        STM = "STM", _("stage manager")
        STN = "STN", _("standards body")
        STR = "STR", _("stereotyper")
        SWD = "SWD", _("software developer")
        TAD = "TAD", _("technical advisor")
        TAU = "TAU", _("television writer")
        TCD = "TCD", _("technical director")
        TCH = "TCH", _("teacher")
        THS = "THS", _("thesis advisor")
        TLD = "TLD", _("television director")
        TLG = "TLG", _("television guest")
        TLH = "TLH", _("television host")
        TLP = "TLP", _("television producer")
        TRC = "TRC", _("transcriber")
        TRL = "TRL", _("translator")
        TYD = "TYD", _("type designer")
        TYG = "TYG", _("typographer")
        UVP = "UVP", _("university place")
        VAC = "VAC", _("voice actor")
        VDG = "VDG", _("videographer")
        VFX = "VFX", _("visual effects provider")
        VOC = "VOC", _("vocalist")
        WAC = "WAC", _("writer of added commentary")
        WAL = "WAL", _("writer of added lyrics")
        WAM = "WAM", _("writer of accompanying material")
        WAT = "WAT", _("writer of added text")
        WAW = "WAW", _("writer of afterword")
        WDC = "WDC", _("woodcutter")
        WDE = "WDE", _("wood engraver")
        WFS = "WFS", _("writer of film story")
        WFT = "WFT", _("writer of intertitles")
        WFW = "WFW", _("writer of foreword")
        WIN = "WIN", _("writer of introduction")
        WIT = "WIT", _("witness")
        WPR = "WPR", _("writer of preface")
        WST = "WST", _("writer of supplementary textual content")
        WTS = "WTS", _("writer of television story")

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
        https://github.com/CRISalid-esr/crisalid-ikg/blob/dev-main/app/models/document_type.py#L9
        """

        ARTICLE = "ARTICLE", _("Article")
        AUDIOVISUAL_DOCUMENT = "AUDIOVISUAL_DOCUMENT", _("Audiovisual Document")
        BLOG_POST = "BLOG_POST", _("Blog Post")
        BOOK = "BOOK", _("Book")
        BOOK_REVIEW = "BOOK_REVIEW", _("Book Review")
        CHAPTER = "CHAPTER", _("Chapter")
        CONFERENCE_OUTPUT = "CONFERENCE_OUTPUT", _("Conference Output")
        CONFERENCE_PAPER = "CONFERENCE_PAPER", _("Conference Paper")
        CONFERENCE_POSTER = "CONFERENCE_POSTER", _("Conference Poster")
        DATA_MANAGEMENT_PLAN = "DATA_MANAGEMENT_PLAN", _("Data Management Plan")
        DATA_PAPER = "DATA_PAPER", _("Data Paper")
        DATASET = "DATASET", _("Dataset")
        DICTIONARY = "DICTIONARY", _("Reference Book")
        DOCUMENT = "DOCUMENT", _("Document")
        DRAWING = "DRAWING", _("Still Image")
        EDITORIAL = "EDITORIAL", _("Editorial")
        ERRATUM = "ERRATUM", _("Erratum")
        GRANT = "GRANT", _("Grant")
        GRAPHICS = "GRAPHICS", _("Still Image")
        IMAGE = "IMAGE", _("Image")
        ILLUSTRATION = "ILLUSTRATION", _("Still Image")
        LECTURE = "LECTURE", _("Lecture")
        LETTER = "LETTER", _("Letter")
        MANUAL = "MANUAL", _("Manual")
        MAP = "MAP", _("Map")
        MASTER_THESIS = "MASTER_THESIS", _("Master Thesis")
        METADATA_DOCUMENT = "METADATA_DOCUMENT", _("Metadata Document")
        NOTE = "NOTE", _("Note")
        OTHER = "OTHER", _("Other")
        PARATEXT = "PARATEXT", _("Metadata Document")
        PATENT = "PATENT", _("Patent")
        PEER_REVIEW = "PEER_REVIEW", _("Peer review")
        PHOTOGRAPHY = "PHOTOGRAPHY", _("Still Image")
        PREPRINT = "PREPRINT", _("Preprint")
        PROCEEDINGS = "PROCEEDINGS", _("Proceedings")
        REFERENCE_ENTRY = "REFERENCE_ENTRY", _("Document")
        REPORT = "REPORT", _("Report")
        RESEARCH_REPORT = "RESEARCH_REPORT", _("Research Report")
        REVIEW = "REVIEW", _("Review Paper")
        REVIEW_ARTICLE = "REVIEW_ARTICLE", _("Review Article")
        SOFTWARE = "SOFTWARE", _("Software")
        STANDARD = "STANDARD", _("Standard")
        STILL_IMAGE = "STILL_IMAGE", _("Still Image")
        TECHNICAL_REPORT = "TECHNICAL_REPORT", _("Technical Report")
        THESIS = "THESIS", _("Thesis")
        WORKING_PAPER = "WORKING_PAPER", _("Working Paper")
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
        Document.DocumentType.AUDIOVISUAL_DOCUMENT.value,
        Document.DocumentType.BLOG_POST.value,
        Document.DocumentType.BOOK.value,
        Document.DocumentType.BOOK_REVIEW.value,
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
