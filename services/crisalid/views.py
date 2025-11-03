import datetime
from collections import Counter
from http import HTTPMethod
from itertools import chain

from django.db.models import Count, QuerySet
from django.db.models.functions import ExtractYear
from django.http import JsonResponse
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import viewsets
from rest_framework.decorators import action

from services.crisalid.models import Document, DocumentContributor, Researcher, DocumentTypeCentralized
from services.crisalid.serializers import DocumentSerializer, ResearcherSerializer


@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter(
                name="document_id",
                description="document id",
                required=False,
                type=int,
            ),
            OpenApiParameter(
                name="crisalid_uid",
                description="crisalid_uid",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="publication_date",
                description="year of publications",
                required=False,
                type=datetime.datetime,
            ),
            OpenApiParameter(
                name="roles",
                description="roles of researcher",
                required=False,
                type=datetime.datetime,
            ),
        ]
    ),
    analytics=extend_schema(
        description="return analytics from documents (numbers of each document by year and number by document types)",
        parameters=[
            OpenApiParameter(
                name="document_id",
                description="document id",
                required=False,
                type=int,
            ),
            OpenApiParameter(
                name="crisalid_uid",
                description="crisalid_uid",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="publication_date",
                description="year of publications",
                required=False,
                type=datetime.datetime,
            ),
            OpenApiParameter(
                name="roles",
                description="roles of researcher",
                required=False,
                type=datetime.datetime,
            ),
        ],
    ),
)
class AbstractDocuementViewSet(viewsets.ReadOnlyModelViewSet):
    """Abstract class to get documents info from docuements types

    :param viewsets: _description_
    :return: _description_
    """
    serializer_class = DocumentSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_fields = ("id", "crisalid_uid", "publication_date")

    def filter_queryset(
        self,
        queryset,
        publication_date=True,
        publication_enabled=True,
        roles_enabled=True,
    ):
        qs = super().filter_queryset(queryset)
        year = self.request.query_params.get("publication_date__year")
        if year and publication_date:
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
        if "document_type" in self.request.query_params and publication_enabled:
            document_type = self.request.query_params.get("document_type")
            qs = qs.filter(document_type=document_type)
        return qs

    def get_queryset(self) -> QuerySet[Document]:
        return (
            Document.objects
            .filter(
                contributors__id=self.kwargs["researcher_id"],
                document_type__in=self.document_types,
            )
            .prefetch_related("identifiers", "contributors__user")
            .order_by("-publication_date")
        )

    @action(detail=False, methods=[HTTPMethod.GET], url_path="analytics")
    def analytics(self, request, *args, **kwargs):
        qs = self.get_queryset()

        # get counted all document_types types
        # use only here the filter_queryset,
        # the next years values need to have all document_types (non filtered)
        document_types = Counter(
            self.filter_queryset(qs, publication_enabled=False)
            .order_by("document_type")
            .values_list("document_type", flat=True)
        )
        document_types = [
            {"name": name, "count": count} for name, count in document_types.items()
        ]

        # order all buplications by years
        limit = self.request.query_params.get("limit")
        years = (
            self.filter_queryset(qs, publication_enabled=False, publication_date=False)
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
            {
                "document_types": document_types,
                "years": list(years),
                "roles": roles,
            }
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

    def get_queryset(self) -> QuerySet:
        return (
            Researcher.objects.all()
            .prefetch_related("identifiers")
            .select_related("user")
        )
