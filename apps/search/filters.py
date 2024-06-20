from django.db.models import Q
from django_filters import rest_framework as filters

from apps.commons.filters import MultiValueCharFilter, UserMultipleIDFilter
from apps.organizations.utils import get_hierarchy_codes

from .models import SearchObject


class SearchObjectFilter(filters.FilterSet):
    # Shared filters
    types = MultiValueCharFilter(field_name="type", lookup_expr="in")
    organizations = MultiValueCharFilter(method="filter_organizations")
    sdgs = MultiValueCharFilter(method="filter_sdgs")

    # User filters
    skills = MultiValueCharFilter(method="filter_skills")

    # Project filters
    languages = MultiValueCharFilter(field_name="project__language", lookup_expr="in")
    categories = MultiValueCharFilter(
        field_name="project__categories__id", lookup_expr="in"
    )
    members = UserMultipleIDFilter(
        field_name="project__groups__users__id", lookup_expr="in", distinct=True
    )
    wikipedia_tags = MultiValueCharFilter(
        field_name="project__wikipedia_tags__wikipedia_qid", lookup_expr="in"
    )
    organization_tags = MultiValueCharFilter(
        field_name="project__organization_tags__id", lookup_expr="in"
    )

    def filter_organizations(self, queryset, name, value):
        return queryset.filter(
            (
                Q(type=SearchObject.SearchObjectType.PEOPLE_GROUP)
                & Q(people_group__organization__code__in=value)
            )
            | (
                Q(type=SearchObject.SearchObjectType.PROJECT)
                & Q(project__organizations__code__in=get_hierarchy_codes(value))
            )
            | (
                Q(type=SearchObject.SearchObjectType.USER)
                & Q(user__groups__organizations__code__in=value)
            )
        ).distinct()

    def filter_sdgs(self, queryset, name, value):
        return queryset.filter(
            (
                Q(type=SearchObject.SearchObjectType.PEOPLE_GROUP)
                & Q(people_group__sdgs__overlap=value)
            )
            | (
                Q(type=SearchObject.SearchObjectType.PROJECT)
                & Q(project__sdgs__overlap=value)
            )
            | (
                Q(type=SearchObject.SearchObjectType.USER)
                & Q(user__sdgs__overlap=value)
            )
        ).distinct()

    def filter_skills(self, queryset, name, value):
        return queryset.filter(
            (
                Q(type=SearchObject.SearchObjectType.USER)
                & Q(people_group__skills__wikipedia_tag__wikipedia_qid__in=value)
            )
            | Q(type=SearchObject.SearchObjectType.PROJECT)
            | Q(type=SearchObject.SearchObjectType.PEOPLE_GROUP)
        ).distinct()

    class Meta:
        model = SearchObject
        fields = [
            "types",
            "organizations",
            "languages",
            "categories",
            "members",
            "sdgs",
            "skills",
            "wikipedia_tags",
            "organization_tags",
        ]
