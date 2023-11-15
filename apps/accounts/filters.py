from django_filters import rest_framework as filters

from apps.commons.filters import MultiValueCharFilter

from .models import PeopleGroup, ProjectUser, Skill


class SkillFilter(filters.FilterSet):
    class Meta:
        model = Skill
        fields = ["user"]


class PeopleGroupFilter(filters.FilterSet):
    organizations = MultiValueCharFilter(method="filter_organizations")
    type = MultiValueCharFilter(field_name="type", lookup_expr="in")  # noqa
    is_root = filters.BooleanFilter(field_name="is_root")

    def filter_organizations(self, queryset, name, value):
        return queryset.filter(organization__code__in=value)

    class Meta:
        model = PeopleGroup
        fields = ["organizations", "type", "is_root"]


class UserFilter(filters.FilterSet):
    organizations = MultiValueCharFilter(method="filter_organizations")

    def filter_organizations(self, queryset, name, value):
        return queryset.filter(groups__organizations__code__in=value).distinct()

    class Meta:
        model = ProjectUser
        fields = ["organizations"]
