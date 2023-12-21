import operator
from functools import reduce

from django.db.models import Q
from django_filters import rest_framework as filters

from apps.accounts.models import ProjectUser
from apps.commons.filters import MultiValueCharFilter, UserMultipleIDFilter
from apps.organizations.utils import get_hierarchy_codes

from .models import Location, Project


class ProjectFilterMixin(filters.FilterSet):
    organizations = MultiValueCharFilter(method="filter_organizations")
    languages = MultiValueCharFilter(field_name="language", lookup_expr="in")
    categories = MultiValueCharFilter(field_name="categories__id", lookup_expr="in")
    members = UserMultipleIDFilter(
        field_name="groups__users__id", lookup_expr="in", distinct=True
    )
    wikipedia_tags = MultiValueCharFilter(
        field_name="wikipedia_tags__wikipedia_qid", lookup_expr="in"
    )
    organization_tags = MultiValueCharFilter(
        field_name="organization_tags__id", lookup_expr="in"
    )
    sdgs = MultiValueCharFilter(field_name="sdgs", lookup_expr="overlap")

    def filter_organizations(self, queryset, name, value):
        return queryset.filter(
            organizations__code__in=get_hierarchy_codes(value)
        ).distinct()


class ProjectFilter(ProjectFilterMixin):
    # filter by member roles with query ?member_role=X,Y,Z
    member_role = MultiValueCharFilter(method="filter_member_role")
    # filter by life_status with query ?life_status=running,completed
    life_status = MultiValueCharFilter(field_name="life_status", lookup_expr="in")
    # filter by creation year with query ?creation_year=2020,2021
    creation_year = MultiValueCharFilter(
        field_name="created_at__year", lookup_expr="in"
    )
    # filter by project ids or slugs with query ?ids=short_id_1,shord_id_2,slug_3
    ids = MultiValueCharFilter(method="filter_ids")

    class Meta:
        model = Project
        fields = [
            "categories",
            "organizations",
            "languages",
            "members",
            "sdgs",
            "wikipedia_tags",
            "organization_tags",
            "member_role",
            "life_status",
            "created_at",
            "ids",
        ]

    def filter_member_role(self, queryset, name, value):
        """Filter project by members with a specific role."""
        if "members" not in self.data:
            return queryset
        members = self.data["members"].split(",")
        members = ProjectUser.get_main_ids(members)
        return queryset.filter(
            Q(groups__users__id__in=members)
            & reduce(operator.or_, (Q(groups__name__contains=role) for role in value))
        ).distinct()

    def filter_ids(self, queryset, name, value):
        """Filter project by id or slug."""
        if "ids" not in self.data:
            return queryset
        ids = self.data["ids"].split(",")
        return queryset.filter(Q(id__in=ids) | Q(slug__in=ids))


class LocationFilter(filters.FilterSet):
    organizations = MultiValueCharFilter(method="filter_organizations")

    class Meta:
        model = Location
        fields = ["organizations"]

    def filter_organizations(self, queryset, name, value):
        return queryset.filter(
            project__organizations__code__in=get_hierarchy_codes(value)
        ).distinct()
