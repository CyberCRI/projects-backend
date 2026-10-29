from django_filters import rest_framework as filters

from services.crisalid.models.award import AwardContributor
from services.crisalid.models.patent import PatentContributor


class PatentContributorFilter(filters.FilterSet):
    name = filters.CharFilter(
        lookup_expr="icontains", label="Search by name", field_name="patent__name"
    )

    description = filters.CharFilter(
        lookup_expr="icontains",
        label="Search by description",
        field_name="patent__desription",
    )

    date = filters.DateFromToRangeFilter(label="Date period")

    class Meta:
        model = PatentContributor
        fields = {
            "date": ["gte", "lte", "exact"],
        }


class AwardContributorFilter(filters.FilterSet):
    name = filters.CharFilter(
        lookup_expr="icontains", label="Search by name", field_name="award__name"
    )

    description = filters.CharFilter(
        lookup_expr="icontains",
        label="Search by description",
        field_name="award__description",
    )

    date = filters.DateFromToRangeFilter(label="Date period")

    class Meta:
        model = AwardContributor
        fields = {
            "date": ["gte", "lte", "exact"],
        }
