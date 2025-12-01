from collections import Counter
from http import HTTPMethod
from itertools import chain

from django.db.models import Count, QuerySet
from django.db.models.functions import ExtractYear
from django.http import JsonResponse
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    extend_schema,
    extend_schema_view,
)
from rest_framework import viewsets
from rest_framework.decorators import action

from apps.commons.permissions import OrganizationPermission
from apps.commons.views import NestedOrganizationViewMixins
from services.crisalid import relators
from services.crisalid.models import (
    Document,
    DocumentContributor,
    DocumentTypeCentralized,
    Identifier,
    Researcher,
)
from services.crisalid.serializers import (
    DocumentAnalyticsSerializer,
    DocumentSerializer,
    ResearcherSerializer,
)
from services.crisalid.utils.views import NestedResearcherViewMixins

OPENAPI_PARAMTERS_DOCUMENTS = [
    OpenApiParameter(
        name="year",
        description="year of publications",
        required=False,
        type=int,
    ),
    OpenApiParameter(
        name="document_type",
        description="type of the documents",
        required=False,
        enum=Document.DocumentType,
    ),
    OpenApiParameter(
        name="roles",
        description="roles of researcher",
        required=False,
        enum=[v for _, v in relators.choices],
        many=True,
    ),
]


@extend_schema_view(
    list=extend_schema(
        description="return list of researcher documents",
        parameters=OPENAPI_PARAMTERS_DOCUMENTS,
    ),
    analytics=extend_schema(
        description="return analytics from documents (numbers of each document by year and number by document types)",
        parameters=OPENAPI_PARAMTERS_DOCUMENTS,
        examples=[
            OpenApiExample(
                "example",
                value={
                    "document_type": {"BookChapter": 32, "ConferenceArticle": 4},
                    "years": [
                        {"year": 2023, "total": 4},
                        {"year": 2022, "total": 2},
                        {"year": 1996, "total": 8},
                    ],
                    "roles": {
                        "author": 43,
                        "animator": 3,
                    },
                },
            )
        ],
    ),
)
class AbstractDocumentViewSet(
    NestedOrganizationViewMixins,
    NestedResearcherViewMixins,
    viewsets.ReadOnlyModelViewSet,
):
    """Abstract class to get documents info from documents types"""

    serializer_class = DocumentSerializer
    permission_classes = (OrganizationPermission,)

    def filter_queryset(
        self,
        queryset,
        year_enabled=True,
        document_type_enabled=True,
        roles_enabled=True,
    ):
        qs = super().filter_queryset(queryset)
        year = self.request.query_params.get("year")
        if year and year_enabled:
            qs = qs.filter(publication_date__year=year)

        # filter only by roles (author, co-authors ...ect)
        roles = [
            r.strip()
            for r in self.request.query_params.get("roles", "").split(",")
            if r.strip()
        ]
        if roles and roles_enabled:
            qs = qs.filter(
                documentcontributor__roles__contains=roles,
                documentcontributor__researcher=self.researcher,
            )

        # filter by pblication_type
        if "document_type" in self.request.query_params and document_type_enabled:
            document_type = self.request.query_params.get("document_type")
            qs = qs.filter(document_type=document_type)
        return qs

    def get_queryset(self) -> QuerySet[Document]:
        return (
            Document.objects.filter(
                contributors=self.researcher,
                document_type__in=self.document_types,
            )
            .prefetch_related("identifiers", "contributors__user")
            .order_by("-publication_date")
        )

    @action(
        detail=True,
        methods=[HTTPMethod.GET],
        url_path="similars",
    )
    def similars(self, request, *args, **kwargs):
        """methods to return similars projects"""
        obj: Document = self.get_object()
        queryset = obj.similars()

        queryset_page = self.paginate_queryset(queryset)
        data = self.serializer_class(
            queryset_page, many=True, context={"request": request}
        )
        return self.get_paginated_response(data.data)

    @action(
        detail=False,
        methods=[HTTPMethod.GET],
        url_path="analytics",
        serializer_class=DocumentAnalyticsSerializer,
    )
    def analytics(self, request, *args, **kwargs):
        """methods to return analytics (how many documents/by year / by document_type) from researcher"""

        qs = self.get_queryset()

        # get counted all document_types types
        # use only here the filter_queryset,
        # the next years values need to have all document_types (non filtered)
        document_types = Counter(
            self.filter_queryset(qs, document_type_enabled=False)
            .order_by("document_type")
            .values_list("document_type", flat=True)
        )

        # order all buplications by years
        limit = self.request.query_params.get("limit")
        years = (
            self.filter_queryset(qs, document_type_enabled=False, year_enabled=False)
            .filter(publication_date__isnull=False)
            .annotate(year=ExtractYear("publication_date"))
            .values("year")
            .annotate(total=Count("id"))
            .order_by("-year")
            .values("total", "year")
        )
        if limit:
            years = years[: int(limit)]

        roles = Counter(
            chain(
                *DocumentContributor.objects.filter(
                    document__in=self.filter_queryset(qs, roles_enabled=False),
                    researcher=self.researcher,
                ).values_list("roles", flat=True)
            )
        )

        return JsonResponse(
            self.serializer_class(
                {
                    "document_types": document_types,
                    "years": list(years),
                    "roles": roles,
                }
            ).data
        )


class PublicationViewSet(AbstractDocumentViewSet):
    document_types = DocumentTypeCentralized.publications


class ConferenceViewSet(AbstractDocumentViewSet):
    document_types = DocumentTypeCentralized.conferences


@extend_schema_view(
    list=extend_schema(
        description="return paginated list of researcher.",
        parameters=[
            OpenApiParameter(
                name="user_id",
                description="ProjectUser id",
                required=False,
                type=str,
            )
        ],
    ),
    search=extend_schema(
        description="return paginated object of researcher filtered by harvester type/values",
        examples=[
            OpenApiExample(
                name="idref",
                description="results with harvester=idref",
                value={
                    "443959954": {
                        "id": 33,
                        "display_name": "marty macfly",
                        "user": "...",
                    },
                    "945584949": {
                        "id": 42,
                        "display_name": "Hubert Bonisseur de La Bath",
                        "user": "...",
                    },
                },
            ),
            OpenApiExample(
                name="eppn",
                description="results with harvester=eppn",
                value={
                    "marty.macfly@sorbonne.fr": {
                        "id": 33,
                        "display_name": "marty macfly",
                        "user": "...",
                    },
                    "Hubert.BonisseurdeLaBath@dgse.fr": {
                        "id": 42,
                        "display_name": "Hubert Bonisseur de La Bath",
                        "user": "...",
                    },
                },
            ),
        ],
        parameters=[
            OpenApiParameter(
                name="harvester",
                description="harvester name",
                required=True,
                enum=Identifier.Harvester,
                examples=[
                    OpenApiExample(
                        "eppn",
                        value="eppn",
                    ),
                    OpenApiExample(
                        "idref",
                        value="idref",
                    ),
                ],
            ),
            OpenApiParameter(
                name="values",
                description="harvester value separate by comas.",
                required=True,
                type=str,
                examples=[
                    OpenApiExample(
                        "eppn",
                        value="marty.macfly@sorbonne.fr,Hubert.BonisseurdeLaBath@dgse.fr",
                    ),
                    OpenApiExample(
                        "idref",
                        value="0984045,049585804,4559932",
                    ),
                ],
            ),
        ],
    ),
)
class ResearcherViewSet(NestedOrganizationViewMixins, viewsets.ReadOnlyModelViewSet):
    serializer_class = ResearcherSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_fields = ("user_id", "id")
    permission_classes = (OrganizationPermission,)

    def get_queryset(self):
        return (
            Researcher.objects.filter(
                user__isnull=False, user__groups__in=(self.organization.get_users(),)
            )
            .prefetch_related("identifiers")
            .select_related("user")
        )

    @action(
        detail=False,
        methods=[HTTPMethod.GET],
        url_path="search",
    )
    def search(self, request, *args, **kwargs):
        """Method to search researchers by harvester type and multiple harvesters value"""
        qs = self.get_queryset()

        harvester_values = request.query_params.get("values").split(",")
        harvester = request.query_params.get("harvester")
        qs = qs.filter(
            identifiers__harvester=harvester, identifiers__value__in=harvester_values
        )

        queryset_page = self.paginate_queryset(qs)
        data = self.serializer_class(
            queryset_page, many=True, context={"request": request}
        ).data
        final = {}
        for user in data:
            for identifier in user["identifiers"]:
                if (
                    identifier["harvester"] == harvester
                    and identifier["value"] in harvester_values
                ):
                    final[identifier["value"]] = user

        return self.get_paginated_response(final)
