from django_filters import rest_framework as filters

from services.crisalid.models.award import Award, AwardContributor
from services.crisalid.models.funding import Funding
from services.crisalid.models.patent import Patent, PatentContributor
from services.crisalid.models.structure import ResearcherStructure
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
