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

from services.crisalid import relators
from services.crisalid.models import (
    Document,
    DocumentContributor,
    DocumentTypeCentralized,
    Researcher,
)
from services.crisalid.serializers import (
    DocumentAnalyticsSerializer,
    DocumentSerializer,
    ResearcherSerializer,
)

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
        enum=list(DocumentTypeCentralized.keys()),
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
class AbstractDocuementViewSet(viewsets.ReadOnlyModelViewSet):
    """Abstract class to get documents info from documents types"""

    serializer_class = DocumentSerializer

    def filter_queryset(
        self,
        queryset,
        year_enabled=True,
        docuement_type_enabled=True,
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
                documentcontributor__researcher__pk=self.kwargs["researcher_id"],
            )

        # filter by pblication_type
        if "document_type" in self.request.query_params and docuement_type_enabled:
            document_type = self.request.query_params.get("document_type")
            qs = qs.filter(document_type=document_type)
        return qs

    def get_queryset(self) -> QuerySet[Document]:
        return (
            Document.objects.filter(
                contributors__id=self.kwargs["researcher_id"],
                document_type__in=self.document_types,
            )
            .prefetch_related("identifiers", "contributors__user")
            .order_by("-publication_date")
        )

    @action(
        detail=False,
        methods=[HTTPMethod.GET],
        url_path="analytics",
        serializer_class=DocumentAnalyticsSerializer,
    )
    def analytics(self, request, *args, **kwargs):
        qs = self.get_queryset()

        # get counted all document_types types
        # use only here the filter_queryset,
        # the next years values need to have all document_types (non filtered)
        document_types = Counter(
            self.filter_queryset(qs, docuement_type_enabled=False)
            .order_by("document_type")
            .values_list("document_type", flat=True)
        )

        # order all buplications by years
        limit = self.request.query_params.get("limit")
        years = (
            self.filter_queryset(qs, docuement_type_enabled=False, year_enabled=False)
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
                    researcher__id=self.kwargs["researcher_id"],
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


class PublicationViewSet(AbstractDocuementViewSet):
    document_types = DocumentTypeCentralized.publications


@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter(
                name="user_id",
                description="ProjectUser id",
                required=False,
                type=str,
            )
        ]
    )
)
class ResearcherViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ResearcherSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_fields = ("user_id", "crisalid_uid", "id")
    queryset = (
        Researcher.objects.all().prefetch_related("identifiers").select_related("user")
    )
