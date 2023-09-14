from django_filters import rest_framework as filters

from apps.accounts.models import PeopleGroup, ProjectUser
from apps.commons.filters import MultiValueCharFilter
from apps.organizations.utils import get_hierarchy_codes
from apps.projects.filters import ProjectFilterMixin
from apps.projects.models import Project


class ProjectSearchFilter(ProjectFilterMixin):
    class Meta:
        model = Project
        fields = [
            "organizations",
            "categories",
            "languages",
            "members",
            "sdgs",
            "wikipedia_tags",
        ]


class UserSearchFilter(filters.FilterSet):
    organizations = MultiValueCharFilter(method="filter_organizations")
    skills = MultiValueCharFilter(method="filter_skills")
    sdgs = MultiValueCharFilter(field_name="sdgs", lookup_expr="overlap")

    def filter_organizations(self, queryset, name, value):
        return queryset.filter(
            groups__organizations__code__in=get_hierarchy_codes(value)
        ).distinct()

    def filter_skills(self, queryset, name, value):
        return queryset.filter(
            skills__wikipedia_tag__wikipedia_qid__in=value
        ).distinct()

    class Meta:
        model = ProjectUser
        fields = [
            "organizations",
            "sdgs",
            "skills",
        ]


class PeopleGroupSearchFilter(filters.FilterSet):
    organizations = MultiValueCharFilter(method="filter_organizations")
    types = MultiValueCharFilter(field_name="type", lookup_expr="in")

    def filter_organizations(self, queryset, name, value):
        return queryset.filter(
            organization__code__in=get_hierarchy_codes(value)
        ).distinct()

    class Meta:
        model = PeopleGroup
        fields = ["organizations", "types"]
