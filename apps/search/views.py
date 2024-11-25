from typing import Any, Dict, List

from algoliasearch_django import algolia_engine
from django.db.models import BigIntegerField, F, Prefetch, Q
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.decorators import action
from rest_framework.settings import api_settings

from apps.commons.utils import ArrayPosition
from apps.commons.views import PaginatedViewSet

from .filters import SearchObjectFilter
from .models import SearchObject
from .pagination import AlgoliaPagination
from .serializers import SearchObjectSerializer


class SearchViewSet(PaginatedViewSet):
    filter_backends = [DjangoFilterBackend]
    serializer_class = SearchObjectSerializer
    filterset_class = SearchObjectFilter
    pagination_class = AlgoliaPagination()
    queryset = SearchObject.objects.all()

    @staticmethod
    def get_extra_api_parameters() -> List[OpenApiParameter]:
        return [
            OpenApiParameter(
                name="types",
                description="Types of objects to filter on, separated by a comma. Can be 'project', 'people_group' or 'user'.",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="organizations",
                description="Codes of the organization to filter on, separated by a comma. Works on projects, groups and users.",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="sdgs",
                description="SDGs to filter on, separated by a comma. Works on projects, groups and users.",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="categories",
                description="Categories ids to filter on, separated by a comma. Works on projects.",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="tags",
                description="Tags IDs to filter on, separated by a comma. Works on projects.",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="members",
                description="Members ids to filter on, separated by a comma. Works on projects.",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="languages",
                description="Languages to filter on, separated by a comma. Works on projects.",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="skills",
                description="Tags IDs of skills to filter on, separated by a comma. Works on users.",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="limit",
                description=f"Number of results to return per page, defaults to {api_settings.PAGE_SIZE}",
                required=False,
                type=int,
            ),
            OpenApiParameter(
                name="offset",
                description="The initial index from which to return the results, defaults to 0.",
                required=False,
                type=int,
            ),
        ]

    def get_filter(self, name):
        """
        Get a filter from the query parameters.
        """
        values = self.request.query_params.get(name, "")
        return values.split(",") if values else []

    def get_type_specific_facet_filter(
        self, facet_filter: List[str], filtered_type: str
    ):
        """
        Make a facet filter work only on a specific type of object.
        """
        if facet_filter:
            unaffected_types = [
                object_type
                for object_type in [
                    SearchObject.SearchObjectType.PROJECT,
                    SearchObject.SearchObjectType.PEOPLE_GROUP,
                    SearchObject.SearchObjectType.USER,
                ]
                if object_type != filtered_type
            ]
            return [*facet_filter, *[f"type:{t}" for t in unaffected_types]]
        return facet_filter

    def get_facet_filters(self):
        """
        Get all the facet filters to apply to the Algolia search.
        """
        facet_filters = [
            ["has_organization:true"],
            ["is_root:false"],
            [f"type:{t}" for t in self.get_filter("types")],
            [f"permissions:{p}" for p in self.get_user_permissions()],
            [f"organizations:{o}" for o in self.get_filter("organizations")],
            [f"sdgs:{s}" for s in self.get_filter("sdgs")],
            self.get_type_specific_facet_filter(
                [f"language:{ln}" for ln in self.get_filter("languages")],
                SearchObject.SearchObjectType.PROJECT,
            ),
            self.get_type_specific_facet_filter(
                [f"skills_filter:{s}" for s in self.get_filter("skills")],
                SearchObject.SearchObjectType.USER,
            ),
            self.get_type_specific_facet_filter(
                [f"can_mentor_filter:{s}" for s in self.get_filter("can_mentor")],
                SearchObject.SearchObjectType.USER,
            ),
            self.get_type_specific_facet_filter(
                [f"needs_mentor_filter:{s}" for s in self.get_filter("needs_mentor")],
                SearchObject.SearchObjectType.USER,
            ),
            self.get_type_specific_facet_filter(
                [f"can_mentor_on_filter:{s}" for s in self.get_filter("can_mentor_on")],
                SearchObject.SearchObjectType.USER,
            ),
            self.get_type_specific_facet_filter(
                [
                    f"needs_mentor_on_filter:{s}"
                    for s in self.get_filter("needs_mentor_on")
                ],
                SearchObject.SearchObjectType.USER,
            ),
            self.get_type_specific_facet_filter(
                [f"categories_filter:{c}" for c in self.get_filter("categories")],
                SearchObject.SearchObjectType.PROJECT,
            ),
            self.get_type_specific_facet_filter(
                [f"tags_filter:{w}" for w in self.get_filter("tags")],
                SearchObject.SearchObjectType.PROJECT,
            ),
            self.get_type_specific_facet_filter(
                [f"members_filter:{m}" for m in self.get_filter("members")],
                SearchObject.SearchObjectType.PROJECT,
            ),
        ]
        return [f for f in facet_filters if f]

    def get_user_permissions(self):
        """
        Get the user's permissions formatted for Algolia.
        """
        public_permissions = [
            "accounts.view_public_peoplegroup",
            "accounts.view_public_projectuser",
            "projects.view_public_project",
        ]
        user = self.request.user
        if user.is_authenticated:
            public_permissions.append(f"accounts.view_projectuser.{user.pk}")
        user_permissions = list(
            filter(
                lambda x: any(
                    x.startswith(s)
                    for s in [
                        # PeopleGroup
                        "accounts.view_peoplegroup",
                        "organizations.view_peoplegroup",
                        "organizations.view_org_peoplegroup",
                        # ProjectUser
                        "accounts.view_projectuser",
                        "organizations.view_projectuser",
                        "organizations.view_org_projectuser",
                        # Project
                        "projects.view_project",
                        "organizations.view_project",
                        "organizations.view_org_project",
                    ]
                ),
                user.get_permissions_representations(),
            )
        )
        return [p.replace(":", "-") for p in public_permissions + user_permissions]

    def _search(self, query: str = "") -> Dict[str, Any]:
        """
        Perform a search on Algolia with the given query.
        """
        groups = self.request.user.get_people_group_queryset()
        projects = self.request.user.get_project_queryset()
        users = self.request.user.get_user_queryset()
        project_prefetch = Prefetch(
            "project", queryset=projects.prefetch_related("categories")
        )
        people_group_prefetch = Prefetch(
            "people_group", queryset=groups.select_related("organization")
        )
        queryset = SearchObject.objects.filter(
            (
                Q(type=SearchObject.SearchObjectType.PEOPLE_GROUP)
                & Q(people_group__in=groups)
            )
            | (Q(type=SearchObject.SearchObjectType.PROJECT) & Q(project__in=projects))
            | (Q(type=SearchObject.SearchObjectType.USER) & Q(user__in=users))
        ).prefetch_related(project_prefetch, people_group_prefetch)
        limit = int(self.request.query_params.get("limit", api_settings.PAGE_SIZE))
        offset = int(self.request.query_params.get("offset", 0))

        params = {
            "distinct": 1,
            "page": offset // limit,
            "hitsPerPage": limit,
            "facetFilters": self.get_facet_filters(),
        }
        response = algolia_engine.raw_search(SearchObject, query, params)
        if response is not None:
            self.pagination_class = AlgoliaPagination(response["nbHits"])
            hits = [h["id"] for h in response["hits"]]
            # Return a queryset of Project sorted with `hits`.
            ordering = ArrayPosition(hits, F("id"), base_field=BigIntegerField())
            queryset = (
                queryset.filter(id__in=hits)
                .annotate(ordering=ordering)
                .order_by("ordering")
            )
        else:
            queryset = queryset.none()
        return queryset

    @extend_schema(
        description="Get Algolia search results by providing a query",
        parameters=get_extra_api_parameters(),
    )
    @action(detail=False, methods=["get"], url_path="(?P<search>.+)")
    def search(self, request, *args, **kwargs):
        """
        Get Algolia search results by providing a query.
        """
        query = self.kwargs["search"]
        queryset = self._search(query)
        return self.get_paginated_list(queryset)

    @extend_schema(
        description="Get Algolia search results with an empty query",
        parameters=get_extra_api_parameters(),
    )
    def list(self, request, *args, **kwargs):
        """
        Get Algolia search results with an empty query.
        """
        queryset = self._search()
        return self.get_paginated_list(queryset)
