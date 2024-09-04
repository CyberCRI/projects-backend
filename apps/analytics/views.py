from collections import Counter, defaultdict

from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.db.models.functions import TruncMonth
from drf_spectacular.utils import OpenApiParameter, extend_schema
from guardian.shortcuts import get_objects_for_user
from rest_framework import mixins
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.commons.permissions import ReadOnly
from apps.misc.models import SDG, WikipediaTag
from apps.organizations.models import Organization
from apps.projects.models import Project

from .exceptions import UnknownPublicationStatusError
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

    def get_organization(self) -> Organization:
        organization_code = self.kwargs["organization_code"]
        return get_object_or_404(Organization, code=organization_code)

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
        authorized_organizations = self.get_queryset()
        current_organization = self.get_organization()

        publication_status = self.request.query_params.get("publication_status", "all")

        projects = Project.objects.all()
        if publication_status != "all":
            projects = projects.filter(publication_status=publication_status)

        if current_organization not in authorized_organizations:
            return Response(
                {"detail": "You do not have the permission to view the analytics for this organization."},
                status=403,
            )
        # Number of project by organization
        count = Count("projects")

        # Retrieve all the projects used for the stats
        projects = projects.filter(organizations__in=[current_organization]).distinct()
        # Number of project per SDG
        by_sdg = [
            {"sdg": sdg, "project_count": projects.filter(sdgs__contains=[sdg]).count()}
            for sdg in SDG
        ]

        by_month = defaultdict(lambda: {"created_count": 0, "updated_count": 0})
        # Number of project created each month
        created_by_month = projects.annotate(month=TruncMonth("created_at"))
        created_by_month = Counter([project.month for project in created_by_month])
        for month, count in created_by_month.items():
            by_month[month.date()]["created_count"] += count

        # Number of project updated each month
        updated_by_month = projects.annotate(month=TruncMonth("updated_at"))
        updated_by_month = Counter([project.month for project in updated_by_month])
        for month, count in updated_by_month.items():
            by_month[month.date()]["updated_count"] += count

        # Top ten wikipedia_tags
        q = Q(projects__in=projects)
        wikipedia_tags = WikipediaTag.objects.annotate(
            project_count=Count("projects", filter=q)
        ).order_by("-project_count")[:10]

        by_month = [{**{"month": k}, **v} for k, v in by_month.items()]
        serializer = StatsSerializer(
            {
                "by_sdg": by_sdg,
                "by_month": by_month,
                "top_tags": wikipedia_tags,
            }
        )
        return Response(serializer.data)
