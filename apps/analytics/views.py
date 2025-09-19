import datetime
from collections import defaultdict

from django.db.models import Count, Q
from django.db.models.functions import TruncMonth
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.accounts.permissions import HasBasePermission
from apps.commons.enums import SDG
from apps.commons.permissions import ReadOnly
from apps.organizations.models import Organization
from apps.organizations.permissions import HasOrganizationPermission
from apps.projects.models import Project
from apps.skills.models import Tag

from .serializers import StatsSerializer


@extend_schema(
    parameters=[
        OpenApiParameter(
            name="publication_status",
            description="Filter project by the given publish status.",
            type=str,
            enum=[
                Project.PublicationStatus.PUBLIC,
                Project.PublicationStatus.PRIVATE,
                Project.PublicationStatus.ORG,
                "all",
            ],
        )
    ]
)
class StatsViewSet(mixins.ListModelMixin, GenericViewSet):
    permission_classes = [
        ReadOnly,
        HasBasePermission("view_stat")
        | HasOrganizationPermission("view_stat", "organizations"),
    ]
    serializer_class = StatsSerializer

    def get_organization(self) -> Organization:
        organization_code = self.kwargs["organization_code"]
        return get_object_or_404(
            Organization.objects.prefetch_related("projects"), code=organization_code
        )

    def get_queryset(self):
        current_organization = self.get_organization()
        publication_status = self.request.query_params.get("publication_status", "all")
        if publication_status == "all":
            return current_organization.projects.all()
        return current_organization.projects.filter(
            publication_status=publication_status
        )

    def list(self, request: Request, *args, **kwargs) -> Response:
        projects_qs = self.get_queryset()

        # Number of project per SDG
        # construct the aggregate Count by SDG
        aggregate = {
            sdg.name: Count("id", filter=Q(sdgs__contains=[sdg])) for sdg in SDG
        }
        aggregate_result = projects_qs.aggregate(**aggregate)
        # recontruct the final dict, the aggregate key is enum str, we need to reconvert str to SDG_ENUM
        by_sdg = [
            {"sdg": SDG[sdg], "project_count": count}
            for sdg, count in aggregate_result.items()
        ]

        # Number of project created each month
        annotate_by_months: list[(datetime.datetime, datetime.datetime)] = (
            projects_qs.annotate(
                create_month=TruncMonth("created_at"),
                update_month=TruncMonth("updated_at"),
            ).values_list("create_month", "update_month")
        )

        # set the total aggregations (same as projects.count())
        projects_total_count = len(annotate_by_months)

        by_month = defaultdict(lambda: {"created_count": 0, "updated_count": 0})
        for create_month, update_month in annotate_by_months:
            by_month[create_month.date()]["created_count"] += 1
            by_month[update_month.date()]["updated_count"] += 1

        # Top ten wikipedia_tags
        tags = (
            Tag.objects.annotate(
                project_count=Count("projects", filter=Q(projects__in=projects_qs))
            )
            .filter(project_count__gt=0)
            .prefetch_related("projects")
            .order_by("-project_count")[:10]
        )

        by_month = [{**{"month": k}, **v} for k, v in by_month.items()]
        serializer = StatsSerializer(
            {
                "total": projects_total_count,
                "by_sdg": by_sdg,
                "by_month": by_month,
                "top_tags": tags,
            }
        )
        return Response(serializer.data)
