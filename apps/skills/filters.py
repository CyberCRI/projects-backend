from django.db.models import Q
from django_filters import filters
from django_filters.rest_framework import FilterSet

from apps.commons.filters import MultiValueCharFilter

from .models import Tag, TagClassification


class TagFilter(FilterSet):
    ids = MultiValueCharFilter(method="filter_ids")

    class Meta:
        model = Tag
        fields = ["ids"]

    def filter_ids(self, queryset, name, value):
        return queryset.filter(id__in=value).distinct()


class TagClassificationFilter(FilterSet):
    type = filters.MultipleChoiceFilter(field_name="type", lookup_expr="in")
    enabled_for = filters.ChoiceFilter(
        method="filter_enabled_for",
        choices=[
            ("skills", "Skills"),
            ("projects", "Projects"),
        ],
    )

    class Meta:
        model = TagClassification
        fields = ["type", "enabled_for"]

    def filter_enabled_for(self, queryset, name: str, values: list[str]):
        q = Q()

        if "skills" in values:
            q |= Q(is_enabled_for_skills=True)

        if "projects" in values:
            q |= Q(is_enabled_for_projects=True)

        return queryset.filter(q)
