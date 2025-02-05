from django.conf import settings
from django.db.models import BigIntegerField, F, Prefetch, Q, QuerySet
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.decorators import action
from rest_framework.settings import api_settings

from apps.commons.utils import ArrayPosition
from apps.commons.views import ListViewSet

from .filters import SearchObjectFilter
from .interface import OpenSearchService
from .models import SearchObject
from .pagination import SearchPagination
from .serializers import SearchObjectSerializer


class SearchViewSet(ListViewSet):
    filterset_class = SearchObjectFilter
    serializer_class = SearchObjectSerializer
    filter_backends = [DjangoFilterBackend]

    def get_queryset(self, order: bool = True) -> QuerySet[SearchObject]:
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
                & Q(people_group__is_root=False)
            )
            | (Q(type=SearchObject.SearchObjectType.PROJECT) & Q(project__in=projects))
            | (Q(type=SearchObject.SearchObjectType.USER) & Q(user__in=users))
        ).prefetch_related(project_prefetch, people_group_prefetch)
        if order:
            return queryset.order_by(F("last_update").desc(nulls_last=True))
        return queryset

    @extend_schema(
        responses=SearchObjectSerializer(many=True),
        filters=[SearchObjectFilter],
        parameters=[
            OpenApiParameter(
                name="limit",
                description="Number of results to return per page.",
                required=False,
                type=int,
            ),
            OpenApiParameter(
                name="offset",
                description="The initial index from which to return the results.",
                required=False,
                type=int,
            ),
            OpenApiParameter(
                name="search_type",
                description="The type of multi_match search to perform: most_fields (default) or best_fields.",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="fuzziness",
                description="The level of tolerance for typos. Can be AUTO or a positive integer (default is 1).",
                required=False,
                type=str,
            ),
        ],
    )
    @action(detail=False, methods=["GET"], url_path="(?P<search>.+)")
    def search(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        search_objects_ids = list(queryset.values_list("id", flat=True))

        query = self.kwargs.get("search", "")
        indices = [
            f"{settings.OPENSEARCH_INDEX_PREFIX}-{index}"
            for index in (
                request.query_params.get("types", "project,user,people_group").split(
                    ","
                )
            )
        ]
        limit = request.query_params.get("limit", api_settings.PAGE_SIZE)
        offset = request.query_params.get("offset", 0)
        search_type = request.query_params.get("search_type", "most_fields")
        fuzziness = request.query_params.get("fuzziness", 1)
        response = OpenSearchService.multi_match_search(
            indices=indices,
            fields=[
                # common
                "content^2",  # project + user + people_group
                "email^2",  # user + people_group
                "members^2",  # project + people_group
                # user
                "given_name^4",
                "family_name^4",
                "job^4",
                "personal_email^2",
                "skills^2",
                "people_groups^1",
                "projects^1",
                # project
                "title^4",
                "purpose^4",
                "tags^3",
                "categories^1",
                # people_group
                "name^4",
            ],
            query=query,
            search_type=search_type,
            limit=limit,
            offset=offset,
            fuzziness=fuzziness,
            search_object_id=search_objects_ids,
        )
        search_objects_ids = [hit.search_object_id for hit in response.hits]
        ordered_queryset = (
            SearchObject.objects.filter(id__in=search_objects_ids)
            .annotate(
                ordering=ArrayPosition(
                    search_objects_ids, F("id"), base_field=BigIntegerField()
                )
            )
            .order_by("ordering")
        )
        self.pagination_class = SearchPagination(response.hits.total.value)
        page = self.paginate_queryset(ordered_queryset)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)
