from rest_framework.routers import DefaultRouter

from apps.commons.urls import organization_router_register

from .views import NewsfeedViewSet, NewsHeaderView, NewsViewSet

router = DefaultRouter()

organization_router_register(
    router,
    r"newsfeed",
    NewsfeedViewSet,
    basename="Newsfeed",
)

organization_router_register(
    router,
    r"news",
    NewsViewSet,
    basename="News",
)

organization_router_register(
    router,
    r"news/(?P<news_id>[^/]+)/header",
    NewsHeaderView,
    basename="News-header",
)
