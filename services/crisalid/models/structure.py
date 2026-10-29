from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.commons.mixins import (
    HasRelatedModules,
    OrganizationRelated,
    TimestampedModelMixin,
)


class CrisalidPeriodModel(models.Model):
    """relation with an optional period of validity"""

    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    class Meta:
        abstract = True

    @staticmethod
    def active_query(prefix: str = "") -> models.Q:
        """filter relations active today"""
        today = timezone.localdate()
        return (
            models.Q(**{f"{prefix}start_date__isnull": True})
            | models.Q(**{f"{prefix}start_date__lte": today})
        ) & (
            models.Q(**{f"{prefix}end_date__isnull": True})
            | models.Q(**{f"{prefix}end_date__gte": today})
        )

    @property
    def is_active(self) -> bool:
        today = timezone.localdate()
        return (self.start_date is None or self.start_date <= today) and (
            self.end_date is None or self.end_date >= today
        )


class Structure(HasRelatedModules, OrganizationRelated, TimestampedModelMixin):
    """
    Represents a research structure (or 'OrganizationUnit') in the Crisalid system.
    """

    class GenericType(models.TextChoices):
        """
        Generic organization type from crisalid
        https://github.com/CRISalid-esr/crisalid-ikg/blob/dev-main/app/models/organization_types.py
        """

        INSTITUTION = "institution", _("Institution")
        INSTITUTION_SUBDIVISION = (
            "institution_subdivision",
            _("Institution subdivision"),
        )
        DOCTORAL_SCHOOL = "doctoral_school", _("Doctoral school")
        UNIT = "unit", _("Unit")
        UNIT_SUBDIVISION = "unit_subdivision", _("Unit subdivision")
        TEAM = "team", _("Team")

    class MissionType(models.TextChoices):
        RESEARCH = "research", _("Research")
        SCIENTIFIC_SERVICES = "scientific_services", _("Scientific services")
        ADMINISTRATIVE_SERVICES = (
            "administrative_services",
            _("Administrative services"),
        )
        TEACHING = "teaching", _("Teaching")

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="crisalid_structures",
    )
    crisalid_uid = models.CharField(max_length=255)
    generic_type = models.CharField(max_length=50, choices=GenericType.choices)
    # national type from crisalid (UMR, FAC, ED ...)
    national_type = models.CharField(max_length=50, blank=True)
    main_mission = models.CharField(
        max_length=50, choices=MissionType.choices, blank=True
    )
    # long label
    name = models.CharField(max_length=255)
    # short label
    acronym = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    external = models.BooleanField(default=False)
    identifiers = models.ManyToManyField(
        "crisalid.Identifier", related_name="structures"
    )
    related_structures = models.ManyToManyField(
        "self",
        through="crisalid.StructureRelation",
        through_fields=("structure", "related_structure"),
        symmetrical=False,
        related_name="reverse_related_structures",
    )
    researchers = models.ManyToManyField(
        "crisalid.Researcher",
        through="crisalid.ResearcherStructure",
        related_name="structures",
    )
    people_group = models.OneToOneField(
        "accounts.PeopleGroup",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="structure",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "crisalid_uid"],
                name="unique_structure_crisalid_uid",
            )
        ]

    def __str__(self):
        return self.name

    def get_related_organizations(self):
        return [self.organization]

    def parents(self) -> models.QuerySet["Structure"]:
        """structures this structure is part of"""
        return Structure.objects.filter(
            StructureRelation.active_query("reverse_relations__"),
            reverse_relations__structure=self,
            reverse_relations__relation_type=StructureRelation.RelationType.PART_OF,
        ).distinct()

    def children(self) -> models.QuerySet["Structure"]:
        """structures part of this structure"""
        return Structure.objects.filter(
            StructureRelation.active_query("relations__"),
            relations__related_structure=self,
            relations__relation_type=StructureRelation.RelationType.PART_OF,
        ).distinct()

    def _walk(self, next_structures) -> list["Structure"]:
        """all structures reached recursively (protected against loops)"""
        visited = {self.pk}
        result = []
        stack = list(next_structures(self))
        while stack:
            structure = stack.pop()
            if structure.pk in visited:
                continue
            visited.add(structure.pk)
            result.append(structure)
            stack.extend(next_structures(structure))
        return result

    def descendants(self) -> list["Structure"]:
        return self._walk(Structure.children)

    def ancestors(self) -> list["Structure"]:
        return self._walk(Structure.parents)


class StructureRelation(CrisalidPeriodModel):
    """Relation between two structures"""

    class RelationType(models.TextChoices):
        PART_OF = "part_of"
        MEMBER_OF = "member_of"

    class Position(models.TextChoices):
        MAIN_SUPERVISION = "main_supervision"
        ASSOCIATED_SUPERVISION = "associated_supervision"
        PARTICIPATING_SUPERVISION = "participating_supervision"

    structure = models.ForeignKey(
        "crisalid.Structure", on_delete=models.CASCADE, related_name="relations"
    )
    related_structure = models.ForeignKey(
        "crisalid.Structure",
        on_delete=models.CASCADE,
        related_name="reverse_relations",
    )
    relation_type = models.CharField(max_length=50, choices=RelationType.choices)
    position = models.CharField(max_length=50, choices=Position.choices, blank=True)

    def __str__(self):
        return f"{self.structure} -{self.relation_type}-> {self.related_structure}"


class ResearcherStructure(CrisalidPeriodModel):
    """Relation between a researcher and a structure (MEMBER_OF / EMPLOYED_AT in crisalid)"""

    class RelationType(models.TextChoices):
        MEMBERSHIP = "membership"
        EMPLOYMENT = "employment"

    class PositionCode(models.TextChoices):
        """HCERES positions of researchers in structures (crisalid "position_code")
        https://github.com/CRISalid-esr/crisalid-ikg/blob/ebdaae75911d504db8e871b7e7cd09f2294b5abf/app/models/positions.py
        """

        PR = "PR", _("Professor")
        DIR = "DIR", _("Director of studies")
        PHYS = "Phys", _("Physicist")
        ASTRO = "Astro", _("Astronomer")
        PUPH = "PUPH", _("University professor - Hospital practitioner")
        PR_AUTMIN = "PR_AutMin", _("Professor in institutions under other ministries")
        ATER = "ATER", _("Temporary teaching and research assistant")
        MCF = "MCF", _("Associate professor")
        PHYS_ADJ = "Phys_adj", _("Assistant physicist")
        ASTRO_ADJ = "Astro_adj", _("Assistant astronomer")
        MCUPH = "MCUPH", _("Associate professor - Hospital practitioner")
        MC_AUTMIN = (
            "MC_AutMin",
            _(
                "Associate or assistant professor in institutions under other ministries"
            ),
        )
        PREM = "PREM", _("Professor emeritus")
        MCFEM = "MCFEM", _("Associate professor emeritus")
        CCA = "CCA", _("Clinical fellow")
        AHU = "AHU", _("University hospital fellow")
        PHU = "PHU", _("University hospital practitioner")
        ECC = "ECC", _("Contract lecturer-researcher")
        PAST = "PAST", _("Associate lecturer-researcher (part-time or full-time)")
        AUTRE_EC = "Autre_EC", _("Other status")
        CHPJ = "ChPJ", _("Junior professor chair")
        DR = "DR", _("Research director and equivalent")
        CR = "CR", _("Research scientist and equivalent")
        CBIB = "CBIB", _("Library curator")
        CPAT = "CPAT", _("Heritage curator")
        DREM = "DREM", _("Research director emeritus")
        CJC = "CJC", _("Young researcher contract (3/5-year fixed term, ATIP-Avenir)")
        C_CONTRACTUEL = "C_contractuel", _("Contract researcher")
        POST_DOC = "Post-doc", _("Postdoctoral researcher")
        INVITE = (
            "Invité",
            _(
                "Foreign visitor: visiting professor or associate researcher, staying at least 3 months in the unit"
            ),
        )
        DOCTEUR = "Docteur", _("Doctor of medicine, pharmacy, etc.")
        AUTRE_CH = "Autre_Ch", _("Other status")
        PRAG = "PRAG", _("Agrégé teacher")
        PCAP = "PCAP", _("Certified teacher")
        IR = "IR", _("Research engineer or equivalent")
        IE = "IE", _("Study engineer or equivalent")
        AI = "AI", _("Assistant engineer or equivalent")
        TECH = "TECH", _("Research technician or equivalent")
        AJT = "AJT", _("Research technical staff and administrative staff")
        BIB = "BIB", _("State librarian")
        BIBAS = "BIBAS", _("Specialised assistant librarian")
        ASBIB = "ASBIB", _("Library assistant")
        MABIB = "MABIB", _("Library storekeeper")
        PH = "PH", _("Hospital practitioner")
        AJH = "AJH", _("Hospital administrative, technical, labour or service staff")
        ASPM = (
            "ASPM",
            _(
                "Nursing assistant, childcare assistant, medical-psychological assistant"
            ),
        )
        SEC = "SEC", _("Hospital secretary")
        TEC = "TEC", _("Hospital technician")
        INF = "INF", _("Nurse")
        SF = "SF", _("Midwife")
        ARC = "ARC", _("Clinical research associate")
        CS = "CS", _("Healthcare manager")
        IGH = "Igh", _("Hospital engineer")
        CP = "CP", _("Project manager (hospital)")
        PATP = "PATP", _("Part-time associate staff")
        CDD = "CDD", _("Fixed-term contract (unspecified category)")
        CDDA = "CDDA", _("Fixed-term contract (category A)")
        CDDB = "CDDB", _("Fixed-term contract (category B)")
        CDDC = "CDDC", _("Fixed-term contract (category C)")
        AUTRE_AP = "Autre_AP", _("Other status")
        STAG = "Stag", _("Intern (BTS, M1 or M2) present at least 3 months in the unit")

    researcher = models.ForeignKey("crisalid.Researcher", on_delete=models.CASCADE)
    structure = models.ForeignKey("crisalid.Structure", on_delete=models.CASCADE)
    relation_type = models.CharField(max_length=50, choices=RelationType.choices)
    position_code = models.CharField(
        max_length=255, choices=PositionCode.choices, blank=True
    )

    def __str__(self):
        return f"{self.researcher} -{self.relation_type}-> {self.structure}"
