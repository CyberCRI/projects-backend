import datetime

from django.db.models import Count, F, QuerySet
from django.db.models.functions import TruncYear
from django.http import JsonResponse
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import viewsets

from services.crisalid.models import Document, Researcher
from services.crisalid.serializers import DocumentSerializer, ResearcherSerializer


class DocumentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DocumentSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_fields = ("id", "crisalid_uid", "publication_date")

    def filter_queryset(self, queryset):
        qs = super().filter_queryset(queryset)

        year = self.request.query_params.get("publication_date__year")
        if year:
            qs = qs.filter(publication_date__year=year)

        return qs

    def get_queryset(self) -> QuerySet:
        return (
            Document.objects.filter(authors__id=self.kwargs["researcher_pk"])
            .prefetch_related("sources", "authors__user")
            .order_by("-publication_date")
        )

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="document_id",
                description="document id",
                required=False,
                type=int,
            ),
            OpenApiParameter(
                name="analytics",
                description="return analytics from documents researchers",
                enum=("info",),
                required=False,
            ),
            OpenApiParameter(
                name="crisalid_uid",
                description="crisalid_uid",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="publication_date",
                description="publication_date",
                required=False,
                type=datetime.datetime,
            ),
        ]
    )
    def list(self, *ar, **kw):
        analytics = self.request.query_params.get("analytics")
        if analytics:
            return self.from_analytics(analytics)
        return super().list(*ar, **kw)

    def from_analytics(self, analytics: str):
        if analytics != "info":
            raise ValueError(f"invalid analytics {analytics!r}")

        qs = self.get_queryset()

        # get counted all documents types
        # use only here the filter_queryset,
        # the next years values need to have all documents (non filtered)
        document_type = (
            self.filter_queryset(qs)
            .values(name=F("sources__document_type"))
            .annotate(count=Count("sources__id"))
            .order_by("sources__document_type")
        )

        # order all buplications by years
        limit = self.request.query_params.get("limit")
        years = (
            qs.filter(publication_date__isnull=False)
            .annotate(year=TruncYear("publication_date"))
            .values("year")
            .annotate(total=Count("id"))
            .order_by("-year")
            .values("total", "year")
        )
        if limit:
            years = years[: int(limit)]

        return JsonResponse(
            {
                "document_type": list(document_type),
                "years": list(years),
            }
        )


class ResearcherViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ResearcherSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_fields = (
        "user_id",
        "crisalid_uid",
        "id",
    )

    def get_queryset(self) -> QuerySet:
        return (
            Researcher.objects.all()
            .prefetch_related(
                "identifiers",
            )
            .select_related("user")
        )

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="user_id",
                description="ProjectUser id",
                required=False,
                type=str,
            ),
        ]
    )
    def list(self, *ar, **kw):
        return super().list(*ar, **kw)
