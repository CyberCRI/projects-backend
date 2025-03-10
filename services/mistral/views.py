from typing import List, Optional, Union

from django.conf import settings
from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.accounts.models import ProjectUser
from apps.accounts.serializers import UserLightSerializer
from apps.commons.cache import redis_cache_viewset_method
from apps.commons.permissions import ReadOnly
from apps.commons.views import MultipleIDViewsetMixin
from apps.organizations.utils import get_below_hierarchy_codes
from apps.projects.models import Project
from apps.projects.serializers import ProjectLightSerializer

from .models import ProjectEmbedding, UserEmbedding


class RecommendationsViewset(MultipleIDViewsetMixin, GenericViewSet):
    filter_backends = [DjangoFilterBackend]
    ordering_fields = []
    permission_classes = [ReadOnly]
    filterset_class = None
    multiple_lookup_fields = [
        (Project, "project_id"),
    ]
    queryset: QuerySet[Union[Project, ProjectUser]]
    serializer_class: Union[ProjectLightSerializer, UserLightSerializer]

    def _list(self, request, *args, **kwargs):
        """
        Redefinition of the ListModelMixin list method to allow for pagination.
        """
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def get_user_embedding(self, user: ProjectUser) -> Optional[List[float]]:
        """
        Return the user's embedding.
        If the user is not authenticated, return None.
        If the embedding is None, create it and return it.
        """
        if user.is_authenticated:
            embedding, _ = UserEmbedding.objects.get_or_create(item=user)
            if embedding.embedding is None:
                embedding = embedding.vectorize()
            return embedding.embedding
        return None

    def get_project_embedding(self, project: Project) -> Optional[List[float]]:
        """
        Return the project's embedding.
        If the embedding is None, create it and return it.
        """
        embedding, _ = ProjectEmbedding.objects.get_or_create(item=project)
        if embedding.embedding is None:
            embedding = embedding.vectorize()
        return embedding.embedding

    def get_queryset_for_project(
        self, project: Project
    ) -> QuerySet[Union[Project, ProjectUser]]:
        """
        Return the queryset of objects to recommend for a given project.
        """
        raise NotImplementedError

    def get_queryset_for_user(
        self, user: ProjectUser
    ) -> QuerySet[Union[Project, ProjectUser]]:
        """
        Return the queryset of objects to recommend for a given user.
        """
        raise NotImplementedError

    def get_queryset(self) -> QuerySet[Union[Project, ProjectUser]]:
        if "project_id" in self.kwargs:
            project = get_object_or_404(
                self.request.user.get_project_queryset(),
                id=self.kwargs["project_id"],
                organizations__code__in=get_below_hierarchy_codes(
                    [self.kwargs["organization_code"]]
                ),
            )
            return self.get_queryset_for_project(project)
        return self.get_queryset_for_user(self.request.user)

    @redis_cache_viewset_method(
        "recommendations", settings.CACHE_RECOMMENDATION_POOL_TTL
    )
    def get_queryset_pool_ids(self, pool: int) -> List[Union[str, int]]:
        queryset = self.get_queryset()[:pool]
        return list(queryset.values_list("id", flat=True))

    @action(
        detail=False,
        methods=["GET"],
        url_path="project/(?P<project_id>[^/.]+)",
        url_name="for-project",
    )
    def project_recommendations(self, request, *args, **kwargs):
        """
        Get recommendations for a project.
        """
        return self._list(request, *args, **kwargs)

    @action(detail=False, methods=["GET"], url_path="user", url_name="for-user")
    def user_recommendations(self, request, *args, **kwargs):
        """
        Get recommendations for a user.
        """
        return self._list(request, *args, **kwargs)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="count",
                description="The number of results to return.",
                type=OpenApiTypes.INT,
                default=4,
            ),
            OpenApiParameter(
                name="pool",
                description="The number of results among which to choose the final results.",
                type=OpenApiTypes.INT,
                default=25,
            ),
        ]
    )
    @action(
        detail=False,
        methods=["GET"],
        url_path="project/(?P<project_id>[^/.]+)/random",
        url_name="random-for-project",
    )
    def random_project_recommendations(self, request, *args, **kwargs):
        """
        Get random recommendations for a project among a pool of recommendations.
        The `count` parameter specifies the number of results to return.
        The `pool` parameter specifies the number of results among which to choose the final results.
        """
        count = int(request.query_params.get("count", 4))
        pool = int(request.query_params.get("pool", 25))
        pool_ids = self.get_queryset_pool_ids(pool)
        queryset = self.queryset.filter(id__in=pool_ids).order_by("?")[:count]
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="count",
                description="The number of results to return.",
                type=OpenApiTypes.INT,
                default=4,
            ),
            OpenApiParameter(
                name="pool",
                description="The number of results among which to choose the final results.",
                type=OpenApiTypes.INT,
                default=25,
            ),
        ]
    )
    @action(
        detail=False,
        methods=["GET"],
        url_path="user/random",
        url_name="random-for-user",
    )
    def random_user_recommendations(self, request, *args, **kwargs):
        """
        Get random recommendations for a user among a pool of recommendations.
        The `count` parameter specifies the number of results to return.
        The `pool` parameter specifies the number of results among which to choose the final results.
        """
        count = int(request.query_params.get("count", 4))
        pool = int(request.query_params.get("pool", 25))
        pool_ids = self.get_queryset_pool_ids(pool)
        queryset = self.queryset.filter(id__in=pool_ids).order_by("?")[:count]
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class ProjectRecommendationsViewset(RecommendationsViewset):
    queryset = Project.objects.all()
    serializer_class = ProjectLightSerializer

    def get_queryset_for_project(self, project: Project) -> QuerySet[Project]:
        queryset = (
            self.request.user.get_project_queryset()
            .filter(
                organizations__code__in=get_below_hierarchy_codes(
                    [self.kwargs["organization_code"]]
                ),
                score__activity__gte=0.37,  # 6 months of inactivity
            )
            .exclude(id=project.id)
            .prefetch_related("categories")
        )
        embedding = self.get_project_embedding(project)
        if embedding is not None and queryset.exists():
            return ProjectEmbedding.vector_search(embedding, queryset)
        return queryset.none()

    def get_queryset_for_user(self, user: ProjectUser) -> QuerySet[Project]:
        queryset = (
            user.get_project_queryset()
            .filter(
                organizations__code__in=get_below_hierarchy_codes(
                    [self.kwargs["organization_code"]]
                ),
                score__activity__gte=0.37,  # 6 months of inactivity
            )
            .prefetch_related("categories")
        )
        embedding = self.get_user_embedding(user)
        if user.is_authenticated:
            queryset = queryset.exclude(groups__users__id=user.id)
        if embedding is not None and queryset.exists():
            return ProjectEmbedding.vector_search(embedding, queryset)
        return queryset.order_by("-score__score")


class UserRecommendationsViewset(RecommendationsViewset):
    queryset = ProjectUser.objects.all()
    serializer_class = UserLightSerializer

    def get_queryset_for_project(self, project: Project) -> QuerySet[ProjectUser]:
        queryset = (
            self.request.user.get_user_queryset()
            .filter(
                groups__organizations__code__in=get_below_hierarchy_codes(
                    [self.kwargs["organization_code"]]
                ),
                score__activity__gte=0.1,  # 49 weeks of inactivity
            )
            .exclude(groups__projects__id=project.id)
        )
        embedding = self.get_project_embedding(project)
        if self.request.user.is_authenticated:
            queryset = queryset.exclude(id=self.request.user.id)
        if embedding is not None and queryset.exists():
            return UserEmbedding.vector_search(embedding, queryset)
        return queryset.none()

    def get_queryset_for_user(self, user: ProjectUser) -> QuerySet[ProjectUser]:
        queryset = user.get_user_queryset().filter(
            groups__organizations__code__in=get_below_hierarchy_codes(
                [self.kwargs["organization_code"]]
            ),
            score__activity__gte=0.1,  # 49 weeks of inactivity
        )
        embedding = self.get_user_embedding(user)
        if user.is_authenticated:
            queryset = queryset.exclude(id=user.id)
        if embedding is not None and queryset.exists():
            return UserEmbedding.vector_search(embedding, queryset)
        return queryset.order_by("-score__score")
