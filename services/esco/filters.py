from django_filters import rest_framework as filters

from apps.commons.filters import MultiValueCharFilter

from .models import EscoTag


class EscoTagFilter(filters.FilterSet):
    type = MultiValueCharFilter(field_name="type", lookup_expr="in")  # noqa
    parents = MultiValueCharFilter(field_name="parents__id", lookup_expr="in")
    children = MultiValueCharFilter(field_name="children__id", lookup_expr="in")
    essential_skills = MultiValueCharFilter(
        field_name="essential_skills__id", lookup_expr="in"
    )
    essential_for = MultiValueCharFilter(
        field_name="essential_for__id", lookup_expr="in"
    )
    optional_skills = MultiValueCharFilter(
        field_name="optional_skills__id", lookup_expr="in"
    )
    optional_for = MultiValueCharFilter(field_name="optional_for__id", lookup_expr="in")

    class Meta:
        model = EscoTag
        fields = [
            "type",
            "parents",
            "children",
            "essential_skills",
            "essential_for",
            "optional_skills",
            "optional_for",
        ]
