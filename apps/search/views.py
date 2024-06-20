from typing import Any, Dict, List

from algoliasearch_django import algolia_engine
from django.db.models import BigIntegerField, F, Q
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.decorators import action
from rest_framework.settings import api_settings

from apps.accounts.models import ProjectUser

from apps.commons.utils import ArrayPosition
from apps.commons.views import PaginatedViewSet

from .filters import SearchObjectFilter
from .pagination import AlgoliaPagination
from .serializers import SearchObjectSerializer
from .models import SearchObject

import logging
logger = logging.getLogger(__name__)


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
                name="wikipedia_tags",
                description="Wikipedia tags QIDs to filter on, separated by a comma. Works on projects.",
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
                description="Wikipedia QIDs of skills to filter on, separated by a comma. Works on users.",
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
        values = self.request.query_params.get(name, "")
        return values.split(",") if values else []

    def get_facet_filters(self):
        facet_filters = [
            [f"type:{t}" for t in self.get_filter("types")],
            [f"permissions:{p}" for p in self.get_user_permissions()],
            [f"organizations:{o}" for o in self.get_filter("organizations")],
            [f"language:{ln}" for ln in self.get_filter("languages")],
            [f"sdgs:{s}" for s in self.get_filter("sdgs")],
            [f"skills_filter:{s}" for s in self.get_filter("skills")],
            [f"categories_filter:{c}" for c in self.get_filter("categories")],
            [f"wikipedia_tags_filter:{t}" for t in self.get_filter("wikipedia_tags")],
            [
                f"organization_tags_filter:{t}"
                for t in self.get_filter("organization_tags")
            ],
            [
                f"members_filter:{m}"
                for m in ProjectUser.get_main_ids(self.get_filter("members"))
            ],
        ]
        return [f for f in facet_filters if f]

    def get_user_permissions(self):
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
        """Add Full-Text Search functionality thanks to Algolia."""
        groups = self.request.user.get_people_group_queryset()
        projects = self.request.user.get_project_queryset()
        users = self.request.user.get_user_queryset()

        queryset = SearchObject.objects.filter(
            (Q(type=SearchObject.SearchObjectType.PEOPLE_GROUP) & Q(people_group__in=groups))
            | (Q(type=SearchObject.SearchObjectType.PROJECT) & Q(project__in=projects))
            | (Q(type=SearchObject.SearchObjectType.USER) & Q(user__in=users))
        )
        logger.error("____________________________________________________")
        logger.error(f"QUERYSET: {queryset.count()}")
        logger.error("____________________________________________________")
        limit = int(self.request.query_params.get("limit", api_settings.PAGE_SIZE))
        offset = int(self.request.query_params.get("offset", 0))

        params = {
            "distinct": 1,
            "page": offset // limit,
            "hitsPerPage": limit,
            "facetFilters": self.get_facet_filters(),
        }
        logger.error("____________________________________________________")
        logger.error(f"PARAMS: {params}")
        logger.error("____________________________________________________")
        response = algolia_engine.raw_search(SearchObject, query, params)
        logger.error("____________________________________________________")
        logger.error(f"RESPONSE: {response}")
        logger.error("____________________________________________________")
        if response is not None:
            self.pagination_class = AlgoliaPagination(response["nbHits"])
            hits = [h["id"] for h in response["hits"]]
            logger.error("____________________________________________________")
            logger.error(f"HITS: {len(hits)}")
            logger.error("____________________________________________________")
            # Return a queryset of Project sorted with `hits`.
            ordering = ArrayPosition(hits, F("id"), base_field=BigIntegerField())
            queryset = (
                queryset.filter(id__in=hits)
                .annotate(ordering=ordering)
                .order_by("ordering")
            )
            logger.error("____________________________________________________")
            logger.error(f"QUERYSET: {queryset.count()}")
            logger.error("____________________________________________________")
        else:
            queryset = queryset.none()
        return queryset

    @extend_schema(
        description="Get Algolia search results by providing a query",
        parameters=get_extra_api_parameters(),
    )
    @action(detail=False, methods=["get"], url_path="(?P<search>.+)")
    def search(self, request, *args, **kwargs):
        query = self.kwargs["search"]
        queryset = self._search(query)
        return self.get_paginated_list(queryset)

    @extend_schema(
        description="Get Algolia search results with an empty query",
        parameters=get_extra_api_parameters(),
    )
    def list(self, request, *args, **kwargs):
        queryset = self._search()
        return self.get_paginated_list(queryset)
