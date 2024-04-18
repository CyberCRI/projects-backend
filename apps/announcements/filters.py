from django_filters import rest_framework as filters

from apps.commons.filters import MultiValueCharFilter
from apps.organizations.utils import get_hierarchy_codes
from apps.projects.models import Project

from .models import Announcement


class AnnouncementFilter(filters.FilterSet):
    organizations = MultiValueCharFilter(method="filter_organizations")
    from_date = filters.DateFilter(field_name="deadline", lookup_expr="gte")
    to_date = filters.DateFilter(field_name="deadline", lookup_expr="lte")

    class Meta:
        model = Announcement
        fields = ["organizations", "from_date", "to_date"]

    def filter_organizations(self, queryset, name, value):
        return queryset.filter(
            project__organizations__code__in=get_hierarchy_codes(value),
            project__publication_status=Project.PublicationStatus.PUBLIC,
        ).distinct()
