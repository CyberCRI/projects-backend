from rest_framework.routers import DefaultRouter

from apps.commons.urls import organization_router_register

from .views import NewsfeedViewSet

router = DefaultRouter()

organization_router_register(
    router,
    r"newsfeed",
    NewsfeedViewSet,
    basename="Newsfeed",
)
