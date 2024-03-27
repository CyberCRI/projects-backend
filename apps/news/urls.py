from rest_framework.routers import DefaultRouter

from apps.commons.urls import news_router_register, organization_router_register

from .views import NewsHeaderView, NewsViewSet

router = DefaultRouter()

organization_router_register(
    router,
    r"news",
    NewsViewSet,
    basename="News",
)

news_router_register(
    router,
    r"header",
    NewsHeaderView,
    basename="News-header",
)
