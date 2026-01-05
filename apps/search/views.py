from django.conf import settings
from django.db.models import F, Q, QuerySet
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.decorators import action
from rest_framework.settings import api_settings

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
        queryset = (
            SearchObject.objects.filter(
                (
                    Q(type=SearchObject.SearchObjectType.PEOPLE_GROUP)
                    & Q(people_group__in=groups)
                    & Q(people_group__is_root=False)
                )
                | (
                    Q(type=SearchObject.SearchObjectType.PROJECT)
                    & Q(project__in=projects)
                )
                | (Q(type=SearchObject.SearchObjectType.USER) & Q(user__in=users))
            )
            .select_related("user", "project__header_image", "people_group")
            .prefetch_related(
                "people_group__organization",
                "project__categories",
            )
        )
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
        search_objects = list(queryset)

        # generate ids for opensearch
        search_objects_ids = [sobj.id for sobj in search_objects]

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
                "content^2",  # project + user + people_group + tag
                "email^2",  # user + people_group
                "members^2",  # project + people_group
                "title^4",  # project + tag
                # user
                "given_name^4",
                "family_name^4",
                "job^4",
                "personal_email^2",
                "skills^2",
                "people_groups^1",
                "projects^1",
                # project
                "purpose^4",
                "tags^3",
                "categories^1",
                # people_group
                "name^4",
                # tag
                "alternative_titles^2",
            ],
            query=query,
            search_type=search_type,
            limit=limit,
            offset=offset,
            fuzziness=fuzziness,
            search_object_id=search_objects_ids,
        )
        search_objects_ids = [hit.search_object_id for hit in response.hits]

        # remove search id not hits in opensearch
        filtered_search_object = [
            obj for obj in search_objects if obj.id in search_objects_ids
        ]
        # sort filtered_search_object by hits index
        ordered_search_objs = sorted(
            filtered_search_object, key=lambda obj: search_objects_ids.index(obj.id)
        )

        self.pagination_class = SearchPagination(response.hits.total.value)
        page = self.paginate_queryset(ordered_search_objs)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)
