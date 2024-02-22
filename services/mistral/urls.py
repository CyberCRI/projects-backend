from rest_framework.routers import DefaultRouter

from apps.commons.urls import organization_router_register, project_router_register

from .views import (
    ProjectRecommendedProjectsViewSet,
    ProjectRecommendedUsersViewSet,
    UserRecommendedProjectsViewSet,
    UserRecommendedUsersViewSet,
)

mistral_router = DefaultRouter()

organization_router_register(
    mistral_router,
    r"recommended-project",
    UserRecommendedProjectsViewSet,
    basename="UserRecommendedProjects",
)
organization_router_register(
    mistral_router,
    r"recommended-user",
    UserRecommendedUsersViewSet,
    basename="UserRecommendedUsers",
)

project_router_register(
    mistral_router,
    r"recommended-project",
    ProjectRecommendedProjectsViewSet,
    basename="ProjectRecommendedProjects",
)
project_router_register(
    mistral_router,
    r"recommended-user",
    ProjectRecommendedUsersViewSet,
    basename="ProjectRecommendedUsers",
)
