from django.db.models import Q
from django_filters import rest_framework as filters

from apps.commons.filters import MultiValueCharFilter
from apps.organizations.utils import get_below_hierarchy_codes

from .models import Announcement


class AnnouncementFilter(filters.FilterSet):
    organizations = MultiValueCharFilter(method="filter_organizations")
    from_date = filters.DateFilter(field_name="deadline", lookup_expr="gte")
    to_date = filters.DateFilter(field_name="deadline", lookup_expr="lte")
    from_date_or_none = filters.DateFilter(method="filter_from_date_or_none")
    to_date_or_none = filters.DateFilter(method="filter_to_date_or_none")

    class Meta:
        model = Announcement
        fields = ["organizations", "from_date", "to_date"]

    def filter_organizations(self, queryset, name, value):
        return queryset.filter(
            project__organizations__code__in=get_below_hierarchy_codes(value)
        ).distinct()

    def filter_from_date_or_none(self, queryset, name, value):
        return queryset.filter(
            Q(deadline__gte=value) | Q(deadline__isnull=True)
        ).distinct()

    def filter_to_date_or_none(self, queryset, name, value):
        return queryset.filter(
            Q(deadline__lte=value) | Q(deadline__isnull=True)
        ).distinct()
