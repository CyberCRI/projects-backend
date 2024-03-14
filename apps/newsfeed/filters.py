from django.db.models import Q
from django_filters import rest_framework as filters

from apps.organizations.utils import get_hierarchy_codes

from .models import Newsfeed


class NewsfeedFilter(filters.FilterSet):
    organization = filters.CharFilter(method="filter_organization")

    class Meta:
        model = Newsfeed
        fields = ["organization"]

    def filter_organization(self, queryset, name, value):
        return queryset.filter(
            Q(project__organizations__code__in=get_hierarchy_codes([value]))
            | Q(
                announcement__project__organizations__code__in=get_hierarchy_codes(
                    [value]
                )
            )
        ).distinct()
