from django_filters import rest_framework as filters

from services.crisalid.models.award import Award, AwardContributor
from services.crisalid.models.funding import Funding
from services.crisalid.models.journal import Journal
from services.crisalid.models.organization import AuthorityOrganization
from services.crisalid.models.patent import Patent, PatentContributor
from services.crisalid.models.researcher import Researcher
from services.crisalid.models.structure import (
    ResearcherStructure,
    Structure,
    StructureRelation,
)
from services.crisalid.models.teaching import Teaching


class PatentFilter(filters.FilterSet):
    name = filters.CharFilter(
        lookup_expr="icontains",
        label="Search by name",
    )

    description = filters.CharFilter(
        lookup_expr="icontains",
        label="Search by description",
    )

    date = filters.DateFromToRangeFilter(label="Date period")

    class Meta:
        model = Patent
        fields = {
            "date": ["gte", "lte", "exact"],
            "name": ["icontains", "exact"],
            "description": ["icontains", "exact"],
        }


class PatentContributorFilter(filters.FilterSet):
    name = filters.CharFilter(
        lookup_expr="icontains", label="Search by name", field_name="patent__name"
    )

    description = filters.CharFilter(
        lookup_expr="icontains",
        label="Search by description",
    )

    date = filters.DateFromToRangeFilter(label="Date period", field_name="patent__date")

    class Meta:
        model = PatentContributor
        fields = {}


class AwardContributorFilter(filters.FilterSet):
    name = filters.CharFilter(
        lookup_expr="icontains", label="Search by name", field_name="award__name"
    )

    description = filters.CharFilter(
        lookup_expr="icontains",
        label="Search by description",
    )

    date = filters.DateFromToRangeFilter(label="Date period")

    class Meta:
        model = AwardContributor
        fields = {
            "date": ["gte", "lte", "exact"],
            "description": ["icontains", "exact"],
        }


class AwardFilter(filters.FilterSet):
    name = filters.CharFilter(
        lookup_expr="icontains",
        label="Search by name",
    )

    description = filters.CharFilter(
        lookup_expr="icontains",
        label="Search by description",
    )

    class Meta:
        model = Award
        fields = {
            "name": ["icontains", "exact"],
            "description": ["icontains", "exact"],
        }


class FundingFilter(filters.FilterSet):
    name = filters.CharFilter(
        field_name="name",
        lookup_expr="icontains",
    )
    description = filters.CharFilter(
        field_name="description",
        lookup_expr="icontains",
    )

    # Currency
    currency = filters.ChoiceFilter(
        field_name="currency",
        choices=Funding.Currency.choices,
    )

    min_price = filters.NumberFilter(
        field_name="prices",
        lookup_expr="gte",
    )
    max_price = filters.NumberFilter(
        field_name="prices",
        lookup_expr="lte",
    )

    start_date = filters.DateFilter(
        field_name="start_date",
        lookup_expr="exact",
    )
    start_date_after = filters.DateFilter(
        field_name="start_date",
        lookup_expr="gte",
    )
    start_date_before = filters.DateFilter(
        field_name="start_date",
        lookup_expr="lte",
    )

    end_date = filters.DateFilter(
        field_name="end_date",
        lookup_expr="exact",
    )
    end_date_after = filters.DateFilter(
        field_name="end_date",
        lookup_expr="gte",
    )
    end_date_before = filters.DateFilter(
        field_name="end_date",
        lookup_expr="lte",
    )

    project = filters.NumberFilter(
        field_name="project__id",
    )

    researcher = filters.NumberFilter(
        field_name="researchers__id",
        distinct=True,
    )

    class Meta:
        model = Funding
        fields = []


class TeachingFilter(filters.FilterSet):
    name = filters.CharFilter(
        field_name="name",
        lookup_expr="icontains",
    )
    description = filters.CharFilter(
        field_name="description",
        lookup_expr="icontains",
    )
    spec = filters.CharFilter(
        field_name="spec",
        lookup_expr="icontains",
    )
    level = filters.CharFilter(
        field_name="level",
        lookup_expr="icontains",
    )

    researcher = filters.NumberFilter(
        field_name="researcher__id",
    )

    domain = filters.NumberFilter(
        field_name="domains__id",
        distinct=True,
    )

    min_domain_level = filters.NumberFilter(
        field_name="teaching_domains__level",
        lookup_expr="gte",
        distinct=True,
    )
    max_domain_level = filters.NumberFilter(
        field_name="teaching_domains__level",
        lookup_expr="lte",
        distinct=True,
    )

    class Meta:
        model = Teaching
        fields = []


class ResearcherStructureFilter(filters.FilterSet):
    structure = filters.NumberFilter(
        field_name="structure__id",
        lookup_expr="exact",
    )

    relation_type = filters.MultipleChoiceFilter(
        field_name="relation_type",
        choices=ResearcherStructure.RelationType.choices,
    )

    position_code = filters.MultipleChoiceFilter(
        field_name="position_code",
        choices=ResearcherStructure.PositionCode.choices,
    )

    class Meta:
        model = ResearcherStructure
        fields = [
            "structure",
            "relation_type",
            "position_code",
        ]


class StructureFilter(filters.FilterSet):
    generic_type = filters.MultipleChoiceFilter(
        choices=Structure.GenericType.choices,
    )
    main_mission = filters.MultipleChoiceFilter(
        choices=Structure.MissionType.choices,
    )

    name = filters.CharFilter(lookup_expr="icontains")
    acronym = filters.CharFilter(lookup_expr="icontains")
    national_type = filters.CharFilter(lookup_expr="iexact")
    external = filters.BooleanFilter()

    researcher = filters.NumberFilter(
        field_name="researchers__id",
        distinct=True,
    )

    class Meta:
        model = Structure
        fields = []


class StructureRelationFilter(filters.FilterSet):
    relation_type = filters.MultipleChoiceFilter(
        choices=StructureRelation.RelationType.choices,
    )
    position = filters.MultipleChoiceFilter(
        choices=StructureRelation.Position.choices,
    )

    structure = filters.NumberFilter(
        field_name="structure_id",
    )
    related_structure = filters.NumberFilter(
        field_name="related_structure_id",
    )

    class Meta:
        model = StructureRelation
        fields = []


class ResearcherFilter(filters.FilterSet):
    given_name = filters.CharFilter(lookup_expr="icontains")
    family_name = filters.CharFilter(lookup_expr="icontains")

    h_index = filters.NumberFilter()
    h_index_min = filters.NumberFilter(
        field_name="h_index",
        lookup_expr="gte",
    )
    h_index_max = filters.NumberFilter(
        field_name="h_index",
        lookup_expr="lte",
    )
    i10_index = filters.NumberFilter()
    i10_index_min = filters.NumberFilter(
        field_name="i10_index",
        lookup_expr="gte",
    )
    i10_index_max = filters.NumberFilter(
        field_name="i10_index",
        lookup_expr="lte",
    )

    structure = filters.NumberFilter(
        field_name="structures__id",
        distinct=True,
    )
    organization = filters.NumberFilter(
        field_name="structures__organization_id",
        distinct=True,
    )

    class Meta:
        model = Researcher
        fields = []


class StrucureResearcherFilter(ResearcherFilter):
    position_code = filters.MultipleChoiceFilter(
        choices=ResearcherStructure.PositionCode.choices,
    )


class AuthorityOrganizationFilter(filters.FilterSet):
    type = filters.MultipleChoiceFilter(
        choices=AuthorityOrganization.OrganizationType.choices,
    )

    name = filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = AuthorityOrganization
        fields = []


class JournalFilter(filters.FilterSet):
    title = filters.CharFilter(lookup_expr="icontains")

    acronym = filters.CharFilter(
        method="filter_acronym",
    )

    def filter_acronym(self, queryset, name, value):
        return queryset.filter(acronym__icontains=[value])

    class Meta:
        model = Journal
        fields = []
