from rest_framework.response import Response
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.decorators import action
from apps.commons.permissions import ReadOnly
from apps.commons.views import ListViewSet
from .serializers import WikibaseItemSerializer
from .interface import WikipediaService
from .pagination import WikipediaPagination



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
                type=str
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
        count = search_continue + len(results)
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
                default="en",
                many=False,
            ),
            OpenApiParameter(
                name="limit",
                description="Maximum number of results in response, default to 5.",
                required=False,
                type=int,
                default=5,
                many=False,
            ),
        ],
        responses={200: {"type": "array", "items": {"type": "string"}}}
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