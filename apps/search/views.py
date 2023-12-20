from typing import Any, Dict, List

from algoliasearch.search_client import SearchClient
from algoliasearch_django import algolia_engine
from django.conf import settings
from django.db.models import BigIntegerField, CharField, F, Prefetch
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.settings import api_settings

from apps.accounts.models import PeopleGroup, ProjectUser
from apps.accounts.serializers import PeopleGroupLightSerializer, UserLightSerializer
from apps.commons.db.functions import ArrayPosition
from apps.commons.views import ListViewSet
from apps.organizations.models import Organization
from apps.organizations.utils import get_hierarchy_codes
from apps.projects.models import Project

from .filters import PeopleGroupSearchFilter, ProjectSearchFilter, UserSearchFilter
from .pagination import AlgoliaPagination
from .serializers import ProjectSearchSerializer


class AlgoliaSearchViewSetMixin(ListViewSet):
    filter_backends = [DjangoFilterBackend]
    serializer_class = None
    pagination_class = AlgoliaPagination()

    @staticmethod
    def get_extra_api_parameters() -> List[OpenApiParameter]:
        return [
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
                name="types",
                description="Types to filter on, separated by a comma. Works on groups.",
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

    def get_serializer_context(self):
        """Add the request to the serializer's context."""
        return {"request": self.request}

    def _search(self, query: str = "") -> Dict[str, Any]:
        raise NotImplementedError

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

    def get_paginated_list(self, queryset):
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class ProjectSearchViewSet(AlgoliaSearchViewSetMixin):
    """Implement search using Algolia."""

    serializer_class = ProjectSearchSerializer
    filterset_class = ProjectSearchFilter
    queryset = Project.objects.all()

    def get_user_projects_permissions(self):
        public_permission = ["projects.view_public_project"]
        user = self.request.user
        user_permissions = list(
            filter(
                lambda x: any(
                    x.startswith(s)
                    for s in [
                        "projects.view_project",
                        "organizations.view_project",
                        "organizations.view_org_project",
                    ]
                ),
                user.get_permissions_representations(),
            )
        )
        return [p.replace(":", "-") for p in public_permission + user_permissions]

    def get_facet_filters(self):
        facet_filters = [
            [
                f"organizations:{o}"
                for o in get_hierarchy_codes(self.get_filter("organizations"))
            ],
            [
                f"organization_tags_filter:{t}"
                for t in self.get_filter("organization_tags")
            ],
            [
                f"members_filter:{m}"
                for m in ProjectUser.get_main_ids(self.get_filter("members"))
            ],
            [f"categories_filter:{c}" for c in self.get_filter("categories")],
            [f"wikipedia_tags_filter:{t}" for t in self.get_filter("wikipedia_tags")],
            [f"language:{ln}" for ln in self.get_filter("languages")],
            [f"sdgs:{s}" for s in self.get_filter("sdgs")],
            [f"permissions:{p}" for p in self.get_user_projects_permissions()],
        ]
        return [f for f in facet_filters if f]

    def _search(self, query: str = "") -> Dict[str, Any]:
        """Add Full-Text Search functionality thanks to Algolia."""
        projects = self.request.user.get_project_queryset()
        limit = int(self.request.query_params.get("limit", api_settings.PAGE_SIZE))
        offset = int(self.request.query_params.get("offset", 0))

        params = {
            "distinct": 1,
            "page": offset // limit,
            "hitsPerPage": limit,
            "facetFilters": self.get_facet_filters(),
        }
        response = algolia_engine.raw_search(Project, query, params)
        if response is not None:
            self.pagination_class = AlgoliaPagination(response["nbHits"])
            hits = [h["id"] for h in response["hits"]]
            # Return a queryset of Project sorted with `hits`.
            ordering = ArrayPosition(hits, F("pk"), base_field=CharField(max_length=8))
            projects = (
                projects.filter(pk__in=hits)
                .annotate(ordering=ordering)
                .order_by("ordering")
            )
        else:
            projects = projects.none()
        organizations = Prefetch(
            "organizations",
            queryset=Organization.objects.select_related(
                "faq", "parent", "banner_image", "logo_image"
            ).prefetch_related("wikipedia_tags"),
        )
        return projects.prefetch_related(organizations, "categories")


class UserSearchViewSet(AlgoliaSearchViewSetMixin):
    """Implement search using Algolia."""

    serializer_class = UserLightSerializer
    filterset_class = UserSearchFilter
    queryset = ProjectUser.objects.all()

    def get_user_users_permissions(self):
        public_permission = ["accounts.view_public_projectuser"]
        user = self.request.user
        if user.is_authenticated:
            public_permission.append(f"accounts.view_projectuser.{user.pk}")
        user_permissions = list(
            filter(
                lambda x: any(
                    x.startswith(s)
                    for s in [
                        "accounts.view_projectuser",
                        "organizations.view_projectuser",
                        "organizations.view_org_projectuser",
                    ]
                ),
                user.get_permissions_representations(),
            )
        )
        return [p.replace(":", "-") for p in public_permission + user_permissions]

    def get_facet_filters(self):
        facet_filters = [
            [f"organizations:{o}" for o in self.get_filter("organizations")],
            [f"skills_filter:{s}" for s in self.get_filter("skills")],
            [f"sdgs:{s}" for s in self.get_filter("sdgs")],
            [f"permissions:{p}" for p in self.get_user_users_permissions()],
        ]
        return [f for f in facet_filters if f]

    def _search(self, query: str = "") -> Dict[str, Any]:
        """Add Full-Text Search functionality thanks to Algolia."""
        users = self.request.user.get_user_queryset()
        limit = int(self.request.query_params.get("limit", api_settings.PAGE_SIZE))
        offset = int(self.request.query_params.get("offset", 0))

        params = {
            "distinct": 1,
            "page": offset // limit,
            "hitsPerPage": limit,
            "facetFilters": self.get_facet_filters(),
        }
        response = algolia_engine.raw_search(ProjectUser, query, params)
        if response is not None:
            self.pagination_class = AlgoliaPagination(response["nbHits"])
            hits = [h["id"] for h in response["hits"]]
            # Return a queryset of Project sorted with `hits`.
            ordering = ArrayPosition(hits, F("id"), base_field=BigIntegerField())
            users = (
                users.filter(id__in=hits)
                .annotate(ordering=ordering)
                .order_by("ordering")
            )
        else:
            users = users.none()
        return users


class PeopleGroupSearchViewSet(AlgoliaSearchViewSetMixin):
    """Implement search using Algolia."""

    serializer_class = PeopleGroupLightSerializer
    filterset_class = PeopleGroupSearchFilter
    queryset = PeopleGroup.objects.all()

    def get_user_groups_permissions(self):
        public_permission = ["accounts.view_public_peoplegroup"]
        user = self.request.user
        user_permissions = list(
            filter(
                lambda x: any(
                    x.startswith(s)
                    for s in [
                        "accounts.view_peoplegroup",
                        "organizations.view_peoplegroup",
                        "organizations.view_org_peoplegroup",
                    ]
                ),
                user.get_permissions_representations(),
            )
        )
        return [p.replace(":", "-") for p in public_permission + user_permissions]

    def get_facet_filters(self):
        facet_filters = [
            [f"organization:{o}" for o in self.get_filter("organizations")],
            [f"type:{s}" for s in self.get_filter("types")],
            [f"sdgs:{s}" for s in self.get_filter("sdgs")],
            [f"permissions:{p}" for p in self.get_user_groups_permissions()],
        ]
        return [f for f in facet_filters if f]

    def _search(self, query: str = "") -> Dict[str, Any]:
        """Add Full-Text Search functionality thanks to Algolia."""
        groups = self.request.user.get_people_group_queryset()
        limit = int(self.request.query_params.get("limit", api_settings.PAGE_SIZE))
        offset = int(self.request.query_params.get("offset", 0))

        params = {
            "distinct": 1,
            "page": offset // limit,
            "hitsPerPage": limit,
            "facetFilters": self.get_facet_filters(),
        }
        response = algolia_engine.raw_search(PeopleGroup, query, params)
        if response is not None:
            self.pagination_class = AlgoliaPagination(response["nbHits"])
            hits = [h["id"] for h in response["hits"]]
            # Return a queryset of Project sorted with `hits`.
            ordering = ArrayPosition(hits, F("id"), base_field=BigIntegerField())
            groups = (
                groups.filter(id__in=hits)
                .annotate(ordering=ordering)
                .order_by("ordering")
            )
        else:
            groups = groups.none()
        return groups


class MultipleSearchViewSet(AlgoliaSearchViewSetMixin):
    """Search people groups, projects and users with one query."""

    client = SearchClient.create(
        settings.ALGOLIA["APPLICATION_ID"], settings.ALGOLIA["API_KEY"]
    )

    def get_user_projects_permissions(self):
        return ProjectSearchViewSet.get_user_projects_permissions(self)

    def get_user_groups_permissions(self):
        return PeopleGroupSearchViewSet.get_user_groups_permissions(self)

    def get_user_users_permissions(self):
        return UserSearchViewSet.get_user_users_permissions(self)

    def get_group_facet_filters(self):
        return PeopleGroupSearchViewSet.get_facet_filters(self)

    def get_user_facet_filters(self):
        return UserSearchViewSet.get_facet_filters(self)

    def get_project_facet_filters(self):
        return ProjectSearchViewSet.get_facet_filters(self)

    def get_project_filters(self):
        filters = {
            "organizations__code__in": get_hierarchy_codes(
                self.get_filter("organizations")
            ),
            "categories__id__in": self.get_filter("categories"),
            "wikipedia_tags__wikipedia_qid__in": self.get_filter("wikipedia_tags"),
            "organization_tags__id__in": self.get_filter("organization_tags"),
            "groups__users__id__in": ProjectUser.get_main_ids(
                self.get_filter("members")
            ),
            "language__in": self.get_filter("languages"),
            "sdgs__overlap": self.get_filter("sdgs"),
        }
        return {k: v for k, v in filters.items() if v}

    def get_group_filters(self):
        filters = {
            "organization__code__in": self.get_filter("organizations"),
            "sdgs__overlap": self.get_filter("sdgs"),
            "type__in": self.get_filter("types"),
        }
        return {k: v for k, v in filters.items() if v}

    def get_user_filters(self):
        filters = {
            "groups__organizations__code__in": self.get_filter("organizations"),
            "skills__wikipedia_tag__wikipedia_qid__in": self.get_filter("skills"),
            "sdgs__overlap": self.get_filter("sdgs"),
        }
        return {k: v for k, v in filters.items() if v}

    def indices_resources(self):
        return {
            f"{settings.ALGOLIA['INDEX_PREFIX']}_project_": {
                "queryset": self.request.user.get_project_queryset(),
                "serializer_class": ProjectSearchSerializer,
                "filtering_method": self.get_project_filters,
                "facet_filtering_method": self.get_project_facet_filters,
                "lookup_field": "id",
                "base_field_type": CharField(max_length=8),
            },
            f"{settings.ALGOLIA['INDEX_PREFIX']}_user_": {
                "queryset": self.request.user.get_user_queryset(),
                "serializer_class": UserLightSerializer,
                "filtering_method": self.get_user_filters,
                "facet_filtering_method": self.get_user_facet_filters,
                "lookup_field": "id",
                "base_field_type": BigIntegerField(),
            },
            f"{settings.ALGOLIA['INDEX_PREFIX']}_group_": {
                "queryset": self.request.user.get_people_group_queryset(),
                "serializer_class": PeopleGroupLightSerializer,
                "filtering_method": self.get_group_filters,
                "facet_filtering_method": self.get_group_facet_filters,
                "lookup_field": "id",
                "base_field_type": BigIntegerField(),
            },
        }

    def _search(self, query: str = "") -> Dict[str, Any]:
        limit = int(self.request.query_params.get("limit", api_settings.PAGE_SIZE))
        offset = int(self.request.query_params.get("offset", 0))
        indices_resources = self.indices_resources()
        algolia_response = self.client.multiple_queries(
            [
                {
                    "indexName": key,
                    "facetFilters": value["facet_filtering_method"](),
                    "query": query,
                    "distinct": 1,
                    "page": offset // limit,
                    "hitsPerPage": limit,
                }
                for key, value in indices_resources.items()
            ]
        )
        algolia_results = algolia_response.get("results", [])
        results = []
        for algolia_result in algolia_results:
            index_resources = indices_resources[algolia_result["index"]]
            hits = [h[index_resources["lookup_field"]] for h in algolia_result["hits"]]
            # Return a queryset of Project sorted with `hits`.
            ordering = ArrayPosition(
                hits,
                F(index_resources["lookup_field"]),
                base_field=index_resources["base_field_type"],
            )
            queryset = (
                index_resources["queryset"]
                .filter(
                    **{
                        f"{index_resources['lookup_field']}__in": hits,
                        **index_resources["filtering_method"](),
                    }
                )
                .annotate(ordering=ordering)
                .order_by("ordering")
            )
            results.append(
                {
                    "index": queryset.model._meta.verbose_name_plural,
                    "count": algolia_result["nbHits"],
                    "results": index_resources["serializer_class"](
                        queryset, many=True, context={"request": self.request}
                    ).data,
                }
            )
        return results

    def get_paginated_list(self, results):
        return Response(results)
