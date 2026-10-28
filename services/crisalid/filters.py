from django_filters import rest_framework as filters

from services.crisalid.models.award import Award
from services.crisalid.models.patent import Patent


class PatentFilter(filters.FilterSet):
    name = filters.CharFilter(lookup_expr="icontains", label="Search by name")

    description = filters.CharFilter(
        lookup_expr="icontains", label="Search by description"
    )

    date = filters.DateFromToRangeFilter(label="Date period")

    class Meta:
        model = Patent
        fields = {
            "name": ["icontains", "exact"],
            "description": ["icontains", "exact"],
            "date": ["gte", "lte", "exact"],
        }


class AwardFilter(filters.FilterSet):
    name = filters.CharFilter(lookup_expr="icontains", label="Search by name")

    description = filters.CharFilter(
        lookup_expr="icontains", label="Search by description"
    )

    date = filters.DateFromToRangeFilter(label="Date period")

    class Meta:
        model = Award
        fields = {
            "name": ["icontains", "exact"],
            "description": ["icontains", "exact"],
            "date": ["gte", "lte", "exact"],
        }
