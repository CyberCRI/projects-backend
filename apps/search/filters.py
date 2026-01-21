from django.db.models import BigIntegerField, Case, F, JSONField, Q, Value, When
from django_filters import rest_framework as filters
from rest_framework.filters import SearchFilter
from rest_framework.settings import api_settings

from apps.commons.filters import MultiValueCharFilter, UserMultipleIDFilter
from apps.commons.utils import ArrayPosition
from apps.organizations.utils import get_below_hierarchy_codes

from .interface import OpenSearchService
from .models import SearchObject


def MultiMatchSearchFieldsFilter(  # noqa: N802
    index: str,
    fields: list[str] | None,
    highlight: list[str] | None = None,
    highlight_size: int = 150,
):
    class _MultiMatchSearchFieldsFilter(SearchFilter):
        def filter_queryset(self, request, queryset, view):
            query = self.get_search_terms(request)
            if isinstance(query, list):
                query = " ".join(query)
            if query:
                limit = request.query_params.get("limit", api_settings.PAGE_SIZE)
                offset = request.query_params.get("offset", 0)
                response = OpenSearchService.multi_match_search(
                    indices=index,
                    fields=fields,
                    query=query,
                    highlight=highlight,
                    highlight_size=highlight_size,
                    limit=limit,
                    offset=offset,
                    id=list(queryset.values_list("id", flat=True)),
                )
                ids = [hit.id for hit in response.hits]
                if not ids:
                    return queryset.none()
                queryset = queryset.filter(id__in=ids).annotate(
                    ordering=ArrayPosition(ids, F("id"), base_field=BigIntegerField())
                )
                if highlight:
                    queryset = queryset.annotate(
                        highlight=Case(
                            *[
                                When(
                                    id=hit.id,
                                    then=Value(
                                        (
                                            hit.meta.highlight.to_dict()
                                            if hasattr(hit.meta, "highlight")
                                            else {}
                                        ),
                                        output_field=JSONField(),
                                    ),
                                )
                                for hit in response.hits
                            ],
                        )
                    )
                return queryset.order_by("ordering")
            return queryset

    return _MultiMatchSearchFieldsFilter


class SearchObjectFilter(filters.FilterSet):
    # Shared filters
    types = MultiValueCharFilter(field_name="type", lookup_expr="in")
    organizations = MultiValueCharFilter(method="filter_organizations")
    sdgs = MultiValueCharFilter(method="filter_sdgs")
    # User filters
    skills = MultiValueCharFilter(method="filter_skills")
    can_mentor = filters.BooleanFilter(method="filter_can_mentor")
    needs_mentor = filters.BooleanFilter(method="filter_needs_mentor")
    can_mentor_on = MultiValueCharFilter(method="filter_can_mentor_on")
    needs_mentor_on = MultiValueCharFilter(method="filter_needs_mentor_on")
    # Project filters
    languages = MultiValueCharFilter(method="filter_languages")
    categories = MultiValueCharFilter(method="filter_categories")
    members = UserMultipleIDFilter(method="filter_members")
    tags = MultiValueCharFilter(method="filter_tags")

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
            Q(user__skills__tag__id__in=value) | Q(type__in=unaffected_types)
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

    def filter_tags(self, queryset, name, value):
        unaffected_types = [
            SearchObject.SearchObjectType.USER,
            SearchObject.SearchObjectType.PEOPLE_GROUP,
        ]
        return queryset.filter(
            Q(project__tags__id__in=value) | Q(type__in=unaffected_types)
        ).distinct()

    def filter_can_mentor(self, queryset, name, value):
        unaffected_types = [
            SearchObject.SearchObjectType.PROJECT,
            SearchObject.SearchObjectType.PEOPLE_GROUP,
        ]
        return queryset.filter(
            Q(user__skills__can_mentor=value) | Q(type__in=unaffected_types)
        ).distinct()

    def filter_needs_mentor(self, queryset, name, value):
        unaffected_types = [
            SearchObject.SearchObjectType.PROJECT,
            SearchObject.SearchObjectType.PEOPLE_GROUP,
        ]
        return queryset.filter(
            Q(user__skills__needs_mentor=value) | Q(type__in=unaffected_types)
        ).distinct()

    def filter_can_mentor_on(self, queryset, name, value):
        unaffected_types = [
            SearchObject.SearchObjectType.PROJECT,
            SearchObject.SearchObjectType.PEOPLE_GROUP,
        ]
        return queryset.filter(
            Q(
                user__skills__can_mentor=True,
                user__skills__tag__id__in=value,
            )
            | Q(type__in=unaffected_types)
        ).distinct()

    def filter_needs_mentor_on(self, queryset, name, value):
        unaffected_types = [
            SearchObject.SearchObjectType.PROJECT,
            SearchObject.SearchObjectType.PEOPLE_GROUP,
        ]
        return queryset.filter(
            Q(
                user__skills__needs_mentor=True,
                user__skills__tag__id__in=value,
            )
            | Q(type__in=unaffected_types)
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
            "tags",
            "can_mentor",
            "needs_mentor",
            "can_mentor_on",
            "needs_mentor_on",
        ]
