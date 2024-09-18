from django_filters import rest_framework as filters

from apps.commons.filters import MultiValueCharFilter

from .models import EscoOccupation, EscoSkill


class EscoSkillFilter(filters.FilterSet):
    parents = MultiValueCharFilter(field_name="parents__id", lookup_expr="in")
    children = MultiValueCharFilter(field_name="children__id", lookup_expr="in")
    essential_skills = MultiValueCharFilter(
        field_name="essential_skills__id", lookup_expr="in"
    )
    essential_for_skills = MultiValueCharFilter(
        field_name="essential_for_skills__id", lookup_expr="in"
    )
    optional_skills = MultiValueCharFilter(
        field_name="optional_skills__id", lookup_expr="in"
    )
    optional_for_skills = MultiValueCharFilter(
        field_name="optional_for_skills__id", lookup_expr="in"
    )
    essential_for_occupations = MultiValueCharFilter(
        field_name="essential_for_occupations__id", lookup_expr="in"
    )
    optional_for_occupations = MultiValueCharFilter(
        field_name="optional_for_occupations__id", lookup_expr="in"
    )

    class Meta:
        model = EscoSkill
        fields = [
            "parents",
            "children",
            "essential_skills",
            "essential_for_skills",
            "optional_skills",
            "optional_for_skills",
            "essential_for_occupations",
            "optional_for_occupations",
        ]


class EscoOccupationFilter(filters.FilterSet):
    parents = MultiValueCharFilter(field_name="parents__id", lookup_expr="in")
    children = MultiValueCharFilter(field_name="children__id", lookup_expr="in")
    essential_skills = MultiValueCharFilter(
        field_name="essential_skills__id", lookup_expr="in"
    )
    optional_skills = MultiValueCharFilter(
        field_name="optional_skills__id", lookup_expr="in"
    )

    class Meta:
        model = EscoOccupation
        fields = [
            "parents",
            "children",
            "essential_skills",
            "optional_skills",
        ]
