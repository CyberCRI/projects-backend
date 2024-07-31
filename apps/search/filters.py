from django.db.models import Q
from django_filters import rest_framework as filters

from apps.commons.filters import MultiValueCharFilter, UserMultipleIDFilter
from apps.organizations.utils import get_below_hierarchy_codes

from .models import SearchObject


class SearchObjectFilter(filters.FilterSet):
    # Shared filters
    types = MultiValueCharFilter(field_name="type", lookup_expr="in")
    organizations = MultiValueCharFilter(method="filter_organizations")
    sdgs = MultiValueCharFilter(method="filter_sdgs")
    # User filters
    skills = MultiValueCharFilter(method="filter_skills")
    # Project filters
    languages = MultiValueCharFilter(method="filter_languages")
    categories = MultiValueCharFilter(method="filter_categories")
    members = UserMultipleIDFilter(method="filter_members")
    wikipedia_tags = MultiValueCharFilter(method="filter_wikipedia_tags")
    organization_tags = MultiValueCharFilter(method="filter_organization_tags")

    def filter_organizations(self, queryset, name, value):
        return queryset.filter(
            Q(project__organizations__code__in=get_below_hierarchy_codes(value))
            | Q(people_group__organization__code__in=value)
            | Q(user__groups__organizations__code__in=value)
        ).distinct()

    def filter_sdgs(self, queryset, name, value):
        return queryset.filter(
            Q(project__sdgs__overlap=value)
            | Q(people_group__sdgs__overlap=value)
            | Q(user__sdgs__overlap=value)
        ).distinct()

    def filter_skills(self, queryset, name, value):
        unaffected_types = [
            SearchObject.SearchObjectType.PROJECT,
            SearchObject.SearchObjectType.PEOPLE_GROUP,
        ]
        return queryset.filter(
            Q(people_group__skills__wikipedia_tag__wikipedia_qid__in=value)
            | Q(type__in=unaffected_types)
        ).distinct()

    def filter_languages(self, queryset, name, value):
        unaffected_types = [
            SearchObject.SearchObjectType.USER,
            SearchObject.SearchObjectType.PEOPLE_GROUP,
        ]
        return queryset.filter(
            Q(project__language__in=value) | Q(type__in=unaffected_types)
        ).distinct()

    def filter_categories(self, queryset, name, value):
        unaffected_types = [
            SearchObject.SearchObjectType.USER,
            SearchObject.SearchObjectType.PEOPLE_GROUP,
        ]
        return queryset.filter(
            Q(project__categories__id__in=value) | Q(type__in=unaffected_types)
        ).distinct()

    def filter_members(self, queryset, name, value):
        unaffected_types = [
            SearchObject.SearchObjectType.USER,
            SearchObject.SearchObjectType.PEOPLE_GROUP,
        ]
        return queryset.filter(
            Q(project__groups__users__id__in=value) | Q(type__in=unaffected_types)
        ).distinct()

    def filter_wikipedia_tags(self, queryset, name, value):
        unaffected_types = [
            SearchObject.SearchObjectType.USER,
            SearchObject.SearchObjectType.PEOPLE_GROUP,
        ]
        return queryset.filter(
            Q(project__wikipedia_tags__wikipedia_qid__in=value)
            | Q(type__in=unaffected_types)
        ).distinct()

    def filter_organization_tags(self, queryset, name, value):
        unaffected_types = [
            SearchObject.SearchObjectType.USER,
            SearchObject.SearchObjectType.PEOPLE_GROUP,
        ]
        return queryset.filter(
            Q(project__organization_tags__id__in=value) | Q(type__in=unaffected_types)
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
