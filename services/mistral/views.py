from django.db.models import QuerySet
from django_filters.rest_framework import DjangoFilterBackend

from apps.accounts.filters import UserFilter
from apps.accounts.serializers import UserLightSerializer
from apps.commons.permissions import ReadOnly
from apps.commons.views import ListViewSet
from apps.organizations.utils import get_hierarchy_codes
from apps.projects.filters import ProjectFilter
from apps.projects.serializers import ProjectLightSerializer

from .models import ProjectEmbedding, UserEmbedding


class ProjectRecommendationViewSet(ListViewSet):
    serializer_class = ProjectLightSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = ProjectFilter
    ordering_fields = []
    permission_classes = [ReadOnly]

    def get_queryset(self) -> QuerySet:
        queryset = self.request.user.get_project_queryset().filter(
            organizations__code__in=get_hierarchy_codes(
                [self.kwargs["organization_code"]]
            )
        )
        if self.request.user.is_authenticated:
            embedding, _ = UserEmbedding.objects.get_or_create(item=self.request.user)
            vector = embedding.embedding or embedding.vectorize().embedding
            return ProjectEmbedding.vector_search(vector, queryset)
        return queryset


class UserRecommendationViewSet(ListViewSet):
    serializer_class = UserLightSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = UserFilter
    ordering_fields = []
    permission_classes = [ReadOnly]

    def get_queryset(self) -> QuerySet:
        queryset = self.request.user.get_user_queryset().filter(
            groups__organizations__code=self.kwargs["organization_code"]
        )
        if self.request.user.is_authenticated:
            embedding, _ = UserEmbedding.objects.get_or_create(item=self.request.user)
            vector = embedding.embedding or embedding.vectorize().embedding
            return UserEmbedding.vector_search(vector, queryset)
        return queryset
