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
    class RolesChoices(models.TextChoices):
        """
        values from https://id.loc.gov/vocabulary/relators.json
        """

        ABR = "abr", _("abridger")
        ACP = "acp", _("art copyist")
        ACT = "act", _("actor")
        ADI = "adi", _("art director")
        ADP = "adp", _("adapter")
        AFT = "aft", _("author of afterword, colophon, etc.")
        ANC = "anc", _("announcer")
        ANL = "anl", _("analyst")
        ANM = "anm", _("animator")
        ANN = "ann", _("annotator")
        ANT = "ant", _("bibliographic antecedent")
        APE = "ape", _("appellee")
        APL = "apl", _("appellant")
        APP = "app", _("applicant")
        AQT = "aqt", _("author in quotations or text abstracts")
        ARC = "arc", _("architect")
        ARD = "ard", _("artistic director")
        ARR = "arr", _("arranger")
        ART = "art", _("artist")
        ASG = "asg", _("assignee")
        ASN = "asn", _("associated name")
        ATO = "ato", _("autographer")
        ATT = "att", _("attributed name")
        AUC = "auc", _("auctioneer")
        AUD = "aud", _("author of dialog")
        AUE = "aue", _("audio engineer")
        AUI = "aui", _("author of introduction, etc.")
        AUP = "aup", _("audio producer")
        AUS = "aus", _("screenwriter")
        AUT = "aut", _("author")
        BDD = "bdd", _("binding designer")
        BJD = "bjd", _("bookjacket designer")
        BKA = "bka", _("book artist")
        BKD = "bkd", _("book designer")
        BKP = "bkp", _("book producer")
        BLW = "blw", _("blurb writer")
        BND = "bnd", _("binder")
        BPD = "bpd", _("bookplate designer")
        BRD = "brd", _("broadcaster")
        BRL = "brl", _("braille embosser")
        BSL = "bsl", _("bookseller")
        CAD = "cad", _("casting director")
        CAS = "cas", _("caster")
        CCP = "ccp", _("conceptor")
        CHR = "chr", _("choreographer")
        CLI = "cli", _("client")
        CLL = "cll", _("calligrapher")
        CLR = "clr", _("colorist")
        CLT = "clt", _("collotyper")
        CMM = "cmm", _("commentator")
        CMP = "cmp", _("composer")
        CMT = "cmt", _("compositor")
        CND = "cnd", _("conductor")
        CNG = "cng", _("cinematographer")
        CNS = "cns", _("censor")
        COE = "coe", _("contestant-appellee")
        COL = "col", _("collector")
        COM = "com", _("compiler")
        CON = "con", _("conservator")
        COP = "cop", _("camera operator")
        COR = "cor", _("collection registrar")
        COS = "cos", _("contestant")
        COT = "cot", _("contestant-appellant")
        COU = "cou", _("court governed")
        COV = "cov", _("cover designer")
        CPC = "cpc", _("copyright claimant")
        CPE = "cpe", _("complainant-appellee")
        CPH = "cph", _("copyright holder")
        CPL = "cpl", _("complainant")
        CPT = "cpt", _("complainant-appellant")
        CRE = "cre", _("creator")
        CRP = "crp", _("correspondent")
        CRR = "crr", _("corrector")
        CRT = "crt", _("court reporter")
        CSL = "csl", _("consultant")
        CSP = "csp", _("consultant to a project")
        CST = "cst", _("costume designer")
        CTB = "ctb", _("contributor")
        CTE = "cte", _("contestee-appellee")
        CTG = "ctg", _("cartographer")
        CTR = "ctr", _("contractor")
        CTS = "cts", _("contestee")
        CTT = "ctt", _("contestee-appellant")
        CUR = "cur", _("curator")
        CWT = "cwt", _("commentator for written text")
        DBD = "dbd", _("dubbing director")
        DBP = "dbp", _("distribution place")
        DFD = "dfd", _("defendant")
        DFE = "dfe", _("defendant-appellee")
        DFT = "dft", _("defendant-appellant")
        DGC = "dgc", _("degree committee member")
        DGG = "dgg", _("degree granting institution")
        DGS = "dgs", _("degree supervisor")
        DIS = "dis", _("dissertant")
        DJO = "djo", _("dj")
        DLN = "dln", _("delineator")
        DNC = "dnc", _("dancer")
        DNR = "dnr", _("donor")
        DPC = "dpc", _("depicted")
        DPT = "dpt", _("depositor")
        DRM = "drm", _("draftsman")
        DRT = "drt", _("director")
        DSR = "dsr", _("designer")
        DST = "dst", _("distributor")
        DTC = "dtc", _("data contributor")
        DTE = "dte", _("dedicatee")
        DTM = "dtm", _("data manager")
        DTO = "dto", _("dedicator")
        DUB = "dub", _("dubious author")
        EDC = "edc", _("editor of compilation")
        EDD = "edd", _("editorial director")
        EDM = "edm", _("editor of moving image work")
        EDT = "edt", _("editor")
        EGR = "egr", _("engraver")
        ELG = "elg", _("electrician")
        ELT = "elt", _("electrotyper")
        ENG = "eng", _("engineer")
        ENJ = "enj", _("enacting jurisdiction")
        ETR = "etr", _("etcher")
        EVP = "evp", _("event place")
        EXP = "exp", _("expert")
        FAC = "fac", _("facsimilist")
        FDS = "fds", _("film distributor")
        FLD = "fld", _("field director")
        FLM = "flm", _("film editor")
        FMD = "fmd", _("film director")
        FMK = "fmk", _("filmmaker")
        FMO = "fmo", _("former owner")
        FMP = "fmp", _("film producer")
        FND = "fnd", _("funder")
        FON = "fon", _("founder")
        FPY = "fpy", _("first party")
        FRG = "frg", _("forger")
        GDV = "gdv", _("game developer")
        GIS = "gis", _("geographic information specialist")
        HIS = "his", _("host institution")
        HNR = "hnr", _("honoree")
        HST = "hst", _("host")
        ILL = "ill", _("illustrator")
        ILU = "ilu", _("illuminator")
        INK = "ink", _("inker")
        INS = "ins", _("inscriber")
        INV = "inv", _("inventor")
        ISB = "isb", _("issuing body")
        ITR = "itr", _("instrumentalist")
        IVE = "ive", _("interviewee")
        IVR = "ivr", _("interviewer")
        JUD = "jud", _("judge")
        JUG = "jug", _("jurisdiction governed")
        LBR = "lbr", _("laboratory")
        LBT = "lbt", _("librettist")
        LDR = "ldr", _("laboratory director")
        LED = "led", _("lead")
        LEE = "lee", _("libelee-appellee")
        LEL = "lel", _("libelee")
        LEN = "len", _("lender")
        LET = "let", _("libelee-appellant")
        LGD = "lgd", _("lighting designer")
        LIE = "lie", _("libelant-appellee")
        LIL = "lil", _("libelant")
        LIT = "lit", _("libelant-appellant")
        LSA = "lsa", _("landscape architect")
        LSE = "lse", _("licensee")
        LSO = "lso", _("licensor")
        LTG = "ltg", _("lithographer")
        LTR = "ltr", _("letterer")
        LYR = "lyr", _("lyricist")
        MCP = "mcp", _("music copyist")
        MDC = "mdc", _("metadata contact")
        MED = "med", _("medium")
        MFP = "mfp", _("manufacture place")
        MFR = "mfr", _("manufacturer")
        MKA = "mka", _("makeup artist")
        MOD = "mod", _("moderator")
        MON = "mon", _("monitor")
        MRB = "mrb", _("marbler")
        MRK = "mrk", _("markup editor")
        MSD = "msd", _("musical director")
        MTE = "mte", _("metal engraver")
        MTK = "mtk", _("minute taker")
        MUP = "mup", _("music programmer")
        MUS = "mus", _("musician")
        MXE = "mxe", _("mixing engineer")
        NAN = "nan", _("news anchor")
        NRT = "nrt", _("narrator")
        ONP = "onp", _("onscreen participant")
        OPN = "opn", _("opponent")
        ORG = "org", _("originator")
        ORM = "orm", _("organizer")
        OSP = "osp", _("onscreen presenter")
        OTH = "oth", _("other")
        OWN = "own", _("owner")
        PAD = "pad", _("place of address")
        PAN = "pan", _("panelist")
        PAT = "pat", _("patron")
        PBD = "pbd", _("publisher director")
        PBL = "pbl", _("publisher")
        PDR = "pdr", _("project director")
        PFR = "pfr", _("proofreader")
        PHT = "pht", _("photographer")
        PLT = "plt", _("platemaker")
        PMA = "pma", _("permitting agency")
        PMN = "pmn", _("production manager")
        PNC = "pnc", _("penciller")
        POP = "pop", _("printer of plates")
        PPM = "ppm", _("papermaker")
        PPT = "ppt", _("puppeteer")
        PRA = "pra", _("praeses")
        PRC = "prc", _("process contact")
        PRD = "prd", _("production personnel")
        PRE = "pre", _("presenter")
        PRF = "prf", _("performer")
        PRG = "prg", _("programmer")
        PRM = "prm", _("printmaker")
        PRN = "prn", _("production company")
        PRO = "pro", _("producer")
        PRP = "prp", _("production place")
        PRS = "prs", _("production designer")
        PRT = "prt", _("printer")
        PRV = "prv", _("provider")
        PTA = "pta", _("patent applicant")
        PTE = "pte", _("plaintiff-appellee")
        PTF = "ptf", _("plaintiff")
        PTH = "pth", _("patent holder")
        PTT = "ptt", _("plaintiff-appellant")
        PUP = "pup", _("publication place")
        RAP = "rap", _("rapporteur")
        RBR = "rbr", _("rubricator")
        RCD = "rcd", _("recordist")
        RCE = "rce", _("recording engineer")
        RCP = "rcp", _("addressee")
        RDD = "rdd", _("radio director")
        RED = "red", _("redaktor")
        REN = "ren", _("renderer")
        RES = "res", _("researcher")
        REV = "rev", _("reviewer")
        RPC = "rpc", _("radio producer")
        RPS = "rps", _("repository")
        RPT = "rpt", _("reporter")
        RPY = "rpy", _("responsible party")
        RSE = "rse", _("respondent-appellee")
        RSG = "rsg", _("restager")
        RSP = "rsp", _("respondent")
        RSR = "rsr", _("restorationist")
        RST = "rst", _("respondent-appellant")
        RTH = "rth", _("research team head")
        RTM = "rtm", _("research team member")
        RXA = "rxa", _("remix artist")
        SAD = "sad", _("scientific advisor")
        SCE = "sce", _("scenarist")
        SCL = "scl", _("sculptor")
        SCR = "scr", _("scribe")
        SDE = "sde", _("sound engineer")
        SDS = "sds", _("sound designer")
        SEC = "sec", _("secretary")
        SFX = "sfx", _("special effects provider")
        SGD = "sgd", _("stage director")
        SGN = "sgn", _("signer")
        SHT = "sht", _("supporting host")
        SLL = "sll", _("seller")
        SNG = "sng", _("singer")
        SPK = "spk", _("speaker")
        SPN = "spn", _("sponsor")
        SPY = "spy", _("second party")
        SRV = "srv", _("surveyor")
        STD = "std", _("set designer")
        STG = "stg", _("setting")
        STL = "stl", _("storyteller")
        STM = "stm", _("stage manager")
        STN = "stn", _("standards body")
        STR = "str", _("stereotyper")
        SWD = "swd", _("software developer")
        TAD = "tad", _("technical advisor")
        TAU = "tau", _("television writer")
        TCD = "tcd", _("technical director")
        TCH = "tch", _("teacher")
        THS = "ths", _("thesis advisor")
        TLD = "tld", _("television director")
        TLG = "tlg", _("television guest")
        TLH = "tlh", _("television host")
        TLP = "tlp", _("television producer")
        TRC = "trc", _("transcriber")
        TRL = "trl", _("translator")
        TYD = "tyd", _("type designer")
        TYG = "tyg", _("typographer")
        UVP = "uvp", _("university place")
        VAC = "vac", _("voice actor")
        VDG = "vdg", _("videographer")
        VFX = "vfx", _("visual effects provider")
        VOC = "voc", _("vocalist")
        WAC = "wac", _("writer of added commentary")
        WAL = "wal", _("writer of added lyrics")
        WAM = "wam", _("writer of accompanying material")
        WAT = "wat", _("writer of added text")
        WAW = "waw", _("writer of afterword")
        WDC = "wdc", _("woodcutter")
        WDE = "wde", _("wood engraver")
        WFS = "wfs", _("writer of film story")
        WFT = "wft", _("writer of intertitles")
        WFW = "wfw", _("writer of foreword")
        WIN = "win", _("writer of introduction")
        WIT = "wit", _("witness")
        WPR = "wpr", _("writer of preface")
        WST = "wst", _("writer of supplementary textual content")
        WTS = "wts", _("writer of television story")

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
