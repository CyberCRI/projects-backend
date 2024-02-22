from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend

from apps.accounts.filters import UserFilter
from apps.accounts.serializers import UserLightSerializer
from apps.commons.permissions import ReadOnly
from apps.commons.views import ListViewSet, MultipleIDViewsetMixin
from apps.organizations.utils import get_hierarchy_codes
from apps.projects.filters import ProjectFilter
from apps.projects.models import Project
from apps.projects.serializers import ProjectLightSerializer

from .models import Embedding, ProjectEmbedding, UserEmbedding


class RecommendationViewSet(ListViewSet):
    """
    Base class for recommendation viewsets.

    To use it, override the class and set the following attributes:
        - return_if_no_embedding: whether to return results if the query embedding is None
        - searched_model: the Embedding model to search for recommendations
        - serializer_class: the serializer to use for the recommendations
        - filterset_class: the filterset to use for the recommendations

    And implement the following methods:
        - get_query_embedding: return the embedding to use for the query
        - get_initial_queryset: return the initial queryset to filter for recommendations
    """

    filter_backends = [DjangoFilterBackend]
    ordering_fields = []
    permission_classes = [ReadOnly]
    return_if_no_embedding: bool = None
    filterset_class = None
    serializer_class = None
    searched_model: Embedding = None

    def get_query_embedding(self) -> Embedding:
        raise NotImplementedError

    def get_initial_queryset(self) -> QuerySet:
        raise NotImplementedError

    def get_queryset(self) -> QuerySet:
        queryset = self.get_initial_queryset()
        embedding = self.get_query_embedding()
        if embedding and embedding.embedding is not None:
            return self.searched_model.vector_search(embedding.embedding, queryset)
        return queryset if self.return_if_no_embedding else queryset.none()


class UserRecommendationViewSet(RecommendationViewSet):
    """
    Base class for recommendation viewsets for users.

    It overrides the `get_query_embedding` method to return the user's embedding.
    """

    return_if_no_embedding = True

    def get_query_embedding(self) -> Embedding:
        """
        Return the user's embedding.
        If the user is not authenticated, return None.
        If the embedding is None, create it and return it.
        """
        if self.request.user.is_authenticated:
            embedding, _ = UserEmbedding.objects.get_or_create(item=self.request.user)
            if embedding.embedding is None:
                embedding = embedding.vectorize()
            return embedding
        return None


class ProjectRecommendationViewSet(MultipleIDViewsetMixin, RecommendationViewSet):
    """
    Base class for recommendation viewsets for projects.

    It overrides the `get_query_embedding` method to return the project's embedding.
    """

    return_if_no_embedding = False
    multiple_lookup_fields = [
        (Project, "project_id"),
    ]

    def get_query_embedding(self) -> Embedding:
        """
        Return the project's embedding.
        If the embedding is None, create it and return it.
        """
        project = self.request.user.get_project_queryset().filter(
            organizations__code__in=get_hierarchy_codes(
                [self.kwargs["organization_code"]]
            ),
            id=self.kwargs["project_id"],
        )
        project = get_object_or_404(project)
        embedding, _ = ProjectEmbedding.objects.get_or_create(item=project)
        if embedding.embedding is None:
            embedding = embedding.vectorize()
        return embedding


class UserRecommendedProjectsViewSet(UserRecommendationViewSet):
    """
    Recommend projects to a user based on the user's embedding.
    """

    searched_model = ProjectEmbedding
    serializer_class = ProjectLightSerializer
    filterset_class = ProjectFilter

    def get_initial_queryset(self) -> QuerySet:
        """
        Return the projects that the user can access in the given organization,
        excluding the projects the user is already in.
        """
        queryset = self.request.user.get_project_queryset().filter(
            organizations__code__in=get_hierarchy_codes(
                [self.kwargs["organization_code"]]
            )
        )
        if self.request.user.is_authenticated:
            return queryset.exclude(groups__users__id=self.request.user.id)
        return queryset


class UserRecommendedUsersViewSet(UserRecommendationViewSet):
    """
    Recommend users to a user based on the user's embedding.
    """

    searched_model = UserEmbedding
    serializer_class = UserLightSerializer
    filterset_class = UserFilter

    def get_initial_queryset(self) -> QuerySet:
        """
        Return the users that the user can access in the given organization,
        excluding themselves.
        """
        queryset = self.request.user.get_user_queryset().filter(
            groups__organizations__code=self.kwargs["organization_code"]
        )
        if self.request.user.is_authenticated:
            return queryset.exclude(id=self.request.user.id)
        return queryset


class ProjectRecommendedProjectsViewSet(ProjectRecommendationViewSet):
    """
    Recommend projects to a project based on the project's embedding.
    """

    searched_model = ProjectEmbedding
    serializer_class = ProjectLightSerializer
    filterset_class = ProjectFilter

    def get_initial_queryset(self) -> QuerySet:
        """
        Return the projects that the user can access in the given organization,
        excluding the project itself.
        """
        return (
            self.request.user.get_project_queryset()
            .filter(
                organizations__code__in=get_hierarchy_codes(
                    [self.kwargs["organization_code"]]
                )
            )
            .exclude(id=self.kwargs["project_id"])
        )


class ProjectRecommendedUsersViewSet(ProjectRecommendationViewSet):
    """
    Recommend users to a project based on the project's embedding.
    """

    searched_model = UserEmbedding
    serializer_class = UserLightSerializer
    filterset_class = UserFilter

    def get_initial_queryset(self) -> QuerySet:
        """
        Return the users that the user can access in the given organization,
        excluding the users already in the project.
        """
        return (
            self.request.user.get_user_queryset()
            .filter(groups__organizations__code=self.kwargs["organization_code"])
            .exclude(groups__projects__id=self.kwargs["project_id"])
        )
