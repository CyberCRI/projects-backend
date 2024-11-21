from django_filters.rest_framework import FilterSet

from apps.commons.filters import MultiValueCharFilter

from .models import Tag


class TagFilter(FilterSet):
    ids = MultiValueCharFilter(method="filter_ids")

    class Meta:
        model = Tag
        fields = ["ids"]

    def filter_ids(self, queryset, name, value):
        return queryset.filter(id__in=value).distinct()
