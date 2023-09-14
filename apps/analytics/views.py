from collections import defaultdict

from django.db.models import Count, Q
from django.db.models.functions import TruncMonth
from drf_spectacular.utils import OpenApiParameter, extend_schema
from guardian.shortcuts import get_objects_for_user
from rest_framework import mixins
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.accounts.permissions import ReadOnly
from apps.misc.models import SDG, WikipediaTag
from apps.organizations.models import Organization
from apps.projects.models import Project

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
                "all",
            ],
        )
    ]
)
class StatsViewSet(mixins.ListModelMixin, GenericViewSet):
    permission_classes = [ReadOnly]
    serializer_class = StatsSerializer

    def get_queryset(self):
        """Retrieve only `Organizations` the user has the `stats:list` permission of."""
        if self.request.user.is_authenticated and self.request.user.has_perm(
            "analytics.view_stat"
        ):
            return Organization.objects.all()
        if self.request.user.is_authenticated:
            return get_objects_for_user(self.request.user, "organizations.view_stat")
        return Organization.objects.none()

    def list(self, request: Request, *args, **kwargs) -> Response:
        organizations = self.get_queryset()
        if organizations.count() == 0:
            return Response(
                {"detail": "You do not have the permission to view the analytics."},
                status=403,
            )
        publication_status = self.request.query_params.get("publication_status", "all")
        if publication_status not in [
            Project.PublicationStatus.PUBLIC,
            Project.PublicationStatus.PRIVATE,
            "all",
        ]:
            raise ValidationError(
                {
                    "publication_status": f"Unknown publication status '{publication_status}"
                }
            )

        # Number of project by organization
        count = Count("projects")
        if publication_status != "all":
            count.filter = Q(projects__publication_status=publication_status)
        organizations = organizations.annotate(project_count=count)

        # Retrieve all the projects used for the stats
        projects = Project.objects.filter(organizations__in=organizations)
        if publication_status != "all":
            projects = projects.filter(publication_status=publication_status)

        # Number of project per SDG
        project_per_sdg = {sdg: 0 for sdg in SDG}
        for p in projects:
            for sdg in p.sdgs:
                project_per_sdg[sdg] += 1
        by_sdg = [
            {"sdg": sdg, "project_count": count}
            for sdg, count in project_per_sdg.items()
        ]

        by_month = defaultdict(lambda: {"created_count": 0, "updated_count": 0})
        # Number of project created each month
        created_by_month = projects.annotate(month=TruncMonth("created_at")).values(
            "month"
        )
        created_by_month = created_by_month.annotate(count=Count("id")).values_list(
            "month", "count"
        )
        for month, count in created_by_month:
            by_month[month.date()]["created_count"] += count

        # Number of project updated each month
        updated_by_month = projects.annotate(month=TruncMonth("updated_at")).values(
            "month"
        )
        updated_by_month = updated_by_month.annotate(count=Count("id")).values_list(
            "month", "count"
        )
        for month, count in updated_by_month:
            by_month[month.date()]["updated_count"] += count

        # Top ten wikipedia_tags
        q = Q(projects__in=projects)
        wikipedia_tags = WikipediaTag.objects.annotate(
            project_count=Count("projects", filter=q)
        ).order_by("-project_count")[:10]

        by_month = [{**{"month": k}, **v} for k, v in by_month.items()]
        serializer = StatsSerializer(
            {
                "by_organization": organizations,
                "by_sdg": by_sdg,
                "by_month": by_month,
                "top_tags": wikipedia_tags,
            }
        )
        return Response(serializer.data)
