from django.db.models import Count, Q
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.commons.permissions import ReadOnly
from apps.commons.views import ListViewSet
from apps.misc.models import WikipediaTag

from .interface import WikipediaService
from .pagination import WikipediaPagination
from .serializers import WikibaseItemSerializer


class WikibaseItemViewset(ListViewSet):
    permission_classes = [ReadOnly]
    http_method_names = ["list", "get"]
    serializer_class = WikibaseItemSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="query",
                description="Search for a specific page name in the Wikipedia database.",
                required=True,
                type=str,
            ),
            OpenApiParameter(
                name="language",
                description="Choose the language you want for your results (en or fr), default to en.",
                required=False,
                type=str,
            ),
        ]
    )
    def list(self, request, *args, **kwargs):
        """
        List all pages returned from wikipedia with a text query
        """
        params = {
            "query": str(self.request.query_params.get("query", "")),
            "language": str(self.request.query_params.get("language", "en")),
            "limit": int(self.request.query_params.get("limit", 100)),
            "offset": int(self.request.query_params.get("offset", 0)),
        }
        response = WikipediaService.search(**params)
        results = response.get("results", [])
        search_continue = response.get("search_continue", 0)
        count = int(search_continue or 0) + len(results)
        paginator = WikipediaPagination(count=count)()
        page = paginator.paginate_queryset(results, request, view=self)
        serializer = self.get_serializer(page, many=True)
        return paginator.get_paginated_response(data=serializer.data)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="query",
                description="Search for a specific page name in the Wikipedia database.",
                required=True,
                type=str,
                many=False,
            ),
            OpenApiParameter(
                name="language",
                description="Choose the language you want for your results (en or fr), default to en.",
                required=False,
                type=str,
                many=False,
            ),
            OpenApiParameter(
                name="limit",
                description="Maximum number of results in response, default to 5.",
                required=False,
                type=int,
                many=False,
            ),
        ],
        responses={200: {"type": "array", "items": {"type": "string"}}},
    )
    @action(detail=False, methods=["GET"])
    def autocomplete(self, request, *args, **kwargs):
        """
        Retrieve a specific wikipedia page name with its qid and all its available translations
        """
        params = {
            "query": str(self.request.query_params.get("query", "")),
            "language": str(self.request.query_params.get("language", "en")),
            "limit": int(self.request.query_params.get("limit", 5)),
        }
        response = WikipediaService.autocomplete(**params)
        return Response(response)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="query",
                description="Search for a specific page name in the Wikipedia database.",
                required=True,
                type=str,
                many=False,
            ),
            OpenApiParameter(
                name="language",
                description="Choose the language you want for your results (en or fr), default to en.",
                required=False,
                type=str,
                many=False,
            ),
            OpenApiParameter(
                name="limit",
                description="Maximum number of results in response, default to 5.",
                required=False,
                type=int,
                many=False,
            ),
        ],
        responses={200: {"type": "array", "items": {"type": "string"}}},
    )
    @action(detail=False, methods=["GET"], url_path="autocomplete-1")
    def autocomplete_local_start(self, request, *args, **kwargs):
        language = self.request.query_params.get("language", "en")
        limit = int(self.request.query_params.get("limit", 5))
        search = self.request.query_params.get("query", "")
        query = {f"name_{language}__unaccent__istartswith": search}
        queryset = (
            WikipediaTag.objects.filter(**query)
            .annotate(
                usage=Count("skill")
                + Count("projects")
                + Count("organization")
                + Count("project_categories")
            )
            .order_by("-usage")[:limit]
        )
        data = queryset.values_list(f"name_{language}", flat=True)
        return Response(data)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="query",
                description="Search for a specific page name in the Wikipedia database.",
                required=True,
                type=str,
                many=False,
            ),
            OpenApiParameter(
                name="language",
                description="Choose the language you want for your results (en or fr), default to en.",
                required=False,
                type=str,
                many=False,
            ),
            OpenApiParameter(
                name="limit",
                description="Maximum number of results in response, default to 5.",
                required=False,
                type=int,
                many=False,
            ),
        ],
        responses={200: {"type": "array", "items": {"type": "string"}}},
    )
    @action(detail=False, methods=["GET"], url_path="autocomplete-2")
    def autocomplete_local_contains(self, request, *args, **kwargs):
        language = self.request.query_params.get("language", "en")
        limit = int(self.request.query_params.get("limit", 5))
        search = self.request.query_params.get("query", "")
        query = {f"name_{language}__unaccent__icontains": search}
        queryset = (
            WikipediaTag.objects.filter(**query)
            .annotate(
                usage=Count("skill")
                + Count("projects")
                + Count("organization")
                + Count("project_categories")
            )
            .order_by("-usage")[:limit]
        )
        data = queryset.values_list(f"name_{language}", flat=True)
        return Response(data)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="query",
                description="Search for a specific page name in the Wikipedia database.",
                required=True,
                type=str,
                many=False,
            ),
            OpenApiParameter(
                name="language",
                description="Choose the language you want for your results (en or fr), default to en.",
                required=False,
                type=str,
                many=False,
            ),
            OpenApiParameter(
                name="limit",
                description="Maximum number of results in response, default to 5.",
                required=False,
                type=int,
                many=False,
            ),
        ],
        responses={200: {"type": "array", "items": {"type": "string"}}},
    )
    @action(detail=False, methods=["GET"], url_path="autocomplete-3")
    def autocomplete_local_mix(self, request, *args, **kwargs):
        language = self.request.query_params.get("language", "en")
        limit = int(self.request.query_params.get("limit", 5))
        search = self.request.query_params.get("query", "")
        queryset = (
            WikipediaTag.objects.filter(
                Q(**{f"name_{language}__unaccent__istartswith": search})
                | Q(**{f"name_{language}__unaccent__icontains": f" {search}"})
            )
            .distinct()
            .annotate(
                usage=Count("skill")
                + Count("projects")
                + Count("organization")
                + Count("project_categories")
            )
            .order_by("-usage")[:limit]
        )
        data = queryset.values_list(f"name_{language}", flat=True)
        return Response(data)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="query",
                description="Search for a specific page name in the Wikipedia database.",
                required=True,
                type=str,
                many=False,
            ),
            OpenApiParameter(
                name="language",
                description="Choose the language you want for your results (en or fr), default to en.",
                required=False,
                type=str,
                many=False,
            ),
            OpenApiParameter(
                name="limit",
                description="Maximum number of results in response, default to 5.",
                required=False,
                type=int,
                many=False,
            ),
        ],
        responses={200: {"type": "array", "items": {"type": "string"}}},
    )
    @action(detail=False, methods=["GET"], url_path="autocomplete-compare")
    def autocomplete_benchmark(self, request, *args, **kwargs):
        api_response = self.autocomplete(request)
        starts_with = self.autocomplete_local_start(request)
        contains = self.autocomplete_local_contains(request)
        mix = self.autocomplete_local_mix(request)
        data = {
            "wikipedia_api": api_response.data,
            "local_starts_with": starts_with.data,
            "local_contains": contains.data,
            "local_mixed": mix.data,
        }
        return Response(data)
