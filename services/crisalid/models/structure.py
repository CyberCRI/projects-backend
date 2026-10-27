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
        )

    def children(self) -> models.QuerySet["Structure"]:
        """structures part of this structure"""
        return Structure.objects.filter(
            StructureRelation.active_query("relations__"),
            relations__related_structure=self,
            relations__relation_type=StructureRelation.RelationType.PART_OF,
        )

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

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["structure", "related_structure", "relation_type"],
                name="unique_structure_relation",
            )
        ]

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

        PR = "PR", _("crisalid.researcherposition.PR")
        DIR = "DIR", _("crisalid.researcherposition.DIR")
        PHYS = "Phys", _("crisalid.researcherposition.PHYS")
        ASTRO = "Astro", _("crisalid.researcherposition.ASTRO")
        PUPH = "PUPH", _("crisalid.researcherposition.PUPH")
        PR_AUTMIN = "PR_AutMin", _("crisalid.researcherposition.PR_AUTMIN")
        ATER = "ATER", _("crisalid.researcherposition.ATER")
        MCF = "MCF", _("crisalid.researcherposition.MCF")
        PHYS_ADJ = "Phys_adj", _("crisalid.researcherposition.PHYS_ADJ")
        ASTRO_ADJ = "Astro_adj", _("crisalid.researcherposition.ASTRO_ADJ")
        MCUPH = "MCUPH", _("crisalid.researcherposition.MCUPH")
        MC_AUTMIN = "MC_AutMin", _("crisalid.researcherposition.MC_AUTMIN")
        PREM = "PREM", _("crisalid.researcherposition.PREM")
        MCFEM = "MCFEM", _("crisalid.researcherposition.MCFEM")
        CCA = "CCA", _("crisalid.researcherposition.CCA")
        AHU = "AHU", _("crisalid.researcherposition.AHU")
        PHU = "PHU", _("crisalid.researcherposition.PHU")
        ECC = "ECC", _("crisalid.researcherposition.ECC")
        PAST = "PAST", _("crisalid.researcherposition.PAST")
        AUTRE_EC = "Autre_EC", _("crisalid.researcherposition.AUTRE_EC")
        CHPJ = "ChPJ", _("crisalid.researcherposition.CHPJ")
        DR = "DR", _("crisalid.researcherposition.DR")
        CR = "CR", _("crisalid.researcherposition.CR")
        CBIB = "CBIB", _("crisalid.researcherposition.CBIB")
        CPAT = "CPAT", _("crisalid.researcherposition.CPAT")
        DREM = "DREM", _("crisalid.researcherposition.DREM")
        CJC = "CJC", _("crisalid.researcherposition.CJC")
        C_CONTRACTUEL = "C_contractuel", _("crisalid.researcherposition.C_CONTRACTUEL")
        POST_DOC = "Post-doc", _("crisalid.researcherposition.POST_DOC")
        INVITE = "Invité", _("crisalid.researcherposition.INVITE")
        DOCTEUR = "Docteur", _("crisalid.researcherposition.DOCTEUR")
        AUTRE_CH = "Autre_Ch", _("crisalid.researcherposition.AUTRE_CH")
        PRAG = "PRAG", _("crisalid.researcherposition.PRAG")
        PCAP = "PCAP", _("crisalid.researcherposition.PCAP")
        IR = "IR", _("crisalid.researcherposition.IR")
        IE = "IE", _("crisalid.researcherposition.IE")
        AI = "AI", _("crisalid.researcherposition.AI")
        TECH = "TECH", _("crisalid.researcherposition.TECH")
        AJT = "AJT", _("crisalid.researcherposition.AJT")
        BIB = "BIB", _("crisalid.researcherposition.BIB")
        BIBAS = "BIBAS", _("crisalid.researcherposition.BIBAS")
        ASBIB = "ASBIB", _("crisalid.researcherposition.ASBIB")
        MABIB = "MABIB", _("crisalid.researcherposition.MABIB")
        PH = "PH", _("crisalid.researcherposition.PH")
        AJH = "AJH", _("crisalid.researcherposition.AJH")
        ASPM = "ASPM", _("crisalid.researcherposition.ASPM")
        SEC = "SEC", _("crisalid.researcherposition.SEC")
        TEC = "TEC", _("crisalid.researcherposition.TEC")
        INF = "INF", _("crisalid.researcherposition.INF")
        SF = "SF", _("crisalid.researcherposition.SF")
        ARC = "ARC", _("crisalid.researcherposition.ARC")
        CS = "CS", _("crisalid.researcherposition.CS")
        IGH = "Igh", _("crisalid.researcherposition.IGH")
        CP = "CP", _("crisalid.researcherposition.CP")
        PATP = "PATP", _("crisalid.researcherposition.PATP")
        CDD = "CDD", _("crisalid.researcherposition.CDD")
        CDDA = "CDDA", _("crisalid.researcherposition.CDDA")
        CDDB = "CDDB", _("crisalid.researcherposition.CDDB")
        CDDC = "CDDC", _("crisalid.researcherposition.CDDC")
        AUTRE_AP = "Autre_AP", _("crisalid.researcherposition.AUTRE_AP")
        STAG = "Stag", _("crisalid.researcherposition.STAG")

    researcher = models.ForeignKey("crisalid.Researcher", on_delete=models.CASCADE)
    structure = models.ForeignKey("crisalid.Structure", on_delete=models.CASCADE)
    relation_type = models.CharField(max_length=50, choices=RelationType.choices)
    position_code = models.CharField(
        max_length=255, choices=PositionCode.choices, blank=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["researcher", "structure", "relation_type"],
                name="unique_researcher_structure",
            )
        ]

    def __str__(self):
        return f"{self.researcher} -{self.relation_type}-> {self.structure}"
