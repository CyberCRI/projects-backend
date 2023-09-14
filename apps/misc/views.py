from django.db.models import QuerySet
from django.http import JsonResponse
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from apps.accounts.permissions import HasBasePermission, ReadOnly
from apps.commons.utils.permissions import map_action_to_permission
from apps.misc import api, filters, models, serializers
from apps.organizations.permissions import HasOrganizationPermission


class WikipediaTagViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.WikipediaTagSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = filters.WikipediaTagFilter
    search_fields = ["name"]
    lookup_field = "wikipedia_qid"

    def get_permissions(self):
        codename = map_action_to_permission(self.action, "wikipediatag")
        if codename:
            self.permission_classes = [
                IsAuthenticatedOrReadOnly,
                ReadOnly | HasBasePermission(codename, "misc"),
            ]
        return super().get_permissions()

    def get_queryset(self) -> QuerySet:
        return models.WikipediaTag.objects.all()


class WikipediaTagWikipediaViewSet(viewsets.ModelViewSet):
    permission_classes = [
        IsAuthenticatedOrReadOnly,
        ReadOnly | HasBasePermission("wikipediatag", "misc"),
    ]
    http_method_names = ["get", "list"]
    lookup_field = "wikipedia_qid"
    serializer_class = serializers.WikipediaTagSerializer
    lookup_value_regex = "[Q0-9]+"
    queryset = models.WikipediaTag.objects.all()

    @extend_schema(
        parameters=[
            OpenApiParameter(name="q", description="query", required=True, type=str),
            OpenApiParameter(
                name="lang",
                description="Choose the language you want for your results :en (by default) or fr",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="max_results",
                description="Maximum number of results in response (default is 20)",
                required=False,
                type=int,
            ),
        ]
    )
    def list(self, request, *args, **kwargs) -> JsonResponse:
        """
        List all pages returned from wikipedia with a text query
        """
        response = api.get_query_from_wikipedia_gw(request.query_params)
        return JsonResponse(data=response.json(), status=response.status_code)

    def retrieve(self, request, *args, **kwargs) -> JsonResponse:
        """
        Retrieve a specific wikipedia page name with its qid and all its available translations
        """
        response = api.get_tag_from_wikipedia_gw(self.kwargs["wikipedia_qid"])
        return JsonResponse(data=response.json(), status=response.status_code)

    @action(detail=False, methods=["get"], url_path=r"disambiguate/(?P<page_id>\d+)")
    def disambiguate(self, request, *args, **kwargs) -> JsonResponse:
        """
        Get a disambiguation page result with the disambiguation page id
        """
        response = api.get_disambiguation_page_from_wikipedia_gw(
            self.kwargs["page_id"], request.query_params
        )
        return JsonResponse(data=response.json(), status=response.status_code)


class TagViewSet(viewsets.ModelViewSet):
    serializer_class = serializers.TagSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_class = filters.TagFilter
    search_fields = ["name"]
    queryset = models.Tag.objects.all()

    def get_permissions(self):
        codename = map_action_to_permission(self.action, "tag")
        if codename:
            self.permission_classes = [
                IsAuthenticatedOrReadOnly,
                ReadOnly
                | HasBasePermission(codename, "misc")
                | HasOrganizationPermission(codename),
            ]
        return super().get_permissions()
