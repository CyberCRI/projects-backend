from django_filters import rest_framework as filters

from apps.commons.filters import MultiValueCharFilter

from .models import Organization, ProjectCategory


class ProjectCategoryFilter(filters.FilterSet):
    # filter by organization id with query ?organization=X
    organization = filters.CharFilter(field_name="organization__code")
    is_root = filters.BooleanFilter(field_name="is_root")

    class Meta:
        model = ProjectCategory
        fields = ["organization", "is_root"]


class OrganizationFilter(filters.FilterSet):
    # filter by organization code with query ?codes=X
    codes = MultiValueCharFilter(field_name="code", lookup_expr="in")
    # filter by tags with query ?tags=X,Y,Z
    tags = MultiValueCharFilter(field_name="tags__id", lookup_expr="in")

    class Meta:
        model = Organization
        fields = ["codes", "tags"]
