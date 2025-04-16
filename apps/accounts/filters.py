from django_filters import rest_framework as filters

from apps.commons.filters import MultiValueCharFilter

from .models import PeopleGroup, ProjectUser


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
    current_org_pk = MultiValueCharFilter(method="filter_current_org_pk")
    current_org_role = MultiValueCharFilter(method="filter_current_org_role")
    can_mentor = filters.BooleanFilter(method="filter_can_mentor")
    needs_mentor = filters.BooleanFilter(method="filter_needs_mentor")
    can_mentor_on = MultiValueCharFilter(method="filter_can_mentor_on")
    needs_mentor_on = MultiValueCharFilter(method="filter_needs_mentor_on")

    def filter_organizations(self, queryset, name, value):
        return queryset.filter(groups__organizations__code__in=value).distinct()

    def filter_current_org_pk(self, queryset, name, value):
        return queryset.filter(groups__organizations__pk__in=value).distinct()

    def filter_current_org_role(self, queryset, name, value):
        """Filter users by role in the current organization."""
        if "current_org_pk" not in self.data:
            return queryset
        organization_pk = self.data["current_org_pk"]
        return queryset.filter(
            groups__name__in=[
                f"organization:#{organization_pk}:{role}" for role in value
            ]
        )

    def filter_can_mentor(self, queryset, name, value):
        return queryset.filter(skills__can_mentor=value).distinct()

    def filter_needs_mentor(self, queryset, name, value):
        return queryset.filter(skills__needs_mentor=value).distinct()

    def filter_can_mentor_on(self, queryset, name, value):
        return queryset.filter(
            skills__can_mentor=True, skills__tag__id__in=value
        ).distinct()

    def filter_needs_mentor_on(self, queryset, name, value):
        return queryset.filter(
            skills__needs_mentor=True, skills__tag__id__in=value
        ).distinct()

    class Meta:
        model = ProjectUser
        fields = [
            "organizations",
            "current_org_role",
            "can_mentor",
            "needs_mentor",
            "can_mentor_on",
            "needs_mentor_on",
        ]
