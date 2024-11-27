from django.db.models import BigIntegerField, F, Q, QuerySet, Prefetch
from drf_spectacular.utils import extend_schema
from opensearchpy import OpenSearch, Search
from rest_framework.decorators import action
from rest_framework.settings import api_settings

from apps.commons.utils import ArrayPosition
from apps.commons.views import ListViewSet

from .filters import SearchObjectFilter
from .models import SearchObject
from .pagination import FixedCountPagination
from .serializers import SearchObjectSerializer


class SearchViewSet(ListViewSet):
    filterset_class = SearchObjectFilter
    serializer_class = SearchObjectSerializer
    client = OpenSearch(
        hosts=[{"host": "opensearch-node", "port": 9200}],
        use_ssl=False,
        verify_certs=False,
    )

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
            )
            | (Q(type=SearchObject.SearchObjectType.PROJECT) & Q(project__in=projects))
            | (Q(type=SearchObject.SearchObjectType.USER) & Q(user__in=users))
        ).prefetch_related(project_prefetch, people_group_prefetch)
        if order:
            # return latest updated first
            return queryset.order_by("-last_update")
        return queryset

    @extend_schema(
        responses=SearchObjectSerializer(many=True),
        filters=[SearchObjectFilter],
    )
    @action(detail=False, methods=["GET"], url_path="(?P<search>.+)")
    def search(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        search_objects_ids = list(queryset.values_list("id", flat=True))

        query = self.kwargs.get("search", "")
        indexes = request.query_params.get("types", "project,user,people_group").split(
            ","
        )

        limit = request.query_params.get("limit", api_settings.PAGE_SIZE)
        offset = request.query_params.get("offset", 0)

        response = (
            Search(
                using=self.client,
                index=indexes,
            )
            .filter("terms", search_object_id=search_objects_ids)
            .query("multi_match", query=query)
            .params(size=limit, from_=offset)
            .execute()
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
        self.pagination_class = FixedCountPagination(response.hits.total.value)
        page = self.paginate_queryset(ordered_queryset)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)
