from rest_framework.routers import DefaultRouter

from apps.commons.urls import organization_router_register

from .views import ProjectRecommendationsViewset, UserRecommendationsViewset

mistral_router = DefaultRouter()

organization_router_register(
    mistral_router,
    r"recommended-project",
    ProjectRecommendationsViewset,
    basename="RecommendedProjects",
)
organization_router_register(
    mistral_router,
    r"recommended-user",
    UserRecommendationsViewset,
    basename="RecommendedUsers",
)
