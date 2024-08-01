from rest_framework.routers import DefaultRouter

from apps.commons.urls import organization_router_register

from .views import (
    EventImagesView,
    EventViewSet,
    InstructionImagesView,
    InstructionViewSet,
    NewsfeedViewSet,
    NewsHeaderView,
    NewsImagesView,
    NewsViewSet,
)

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

organization_router_register(
    router,
    r"news/(?P<news_id>[^/]+)/image",
    NewsImagesView,
    basename="News-images",
)

organization_router_register(
    router,
    r"event",
    EventViewSet,
    basename="Event",
)

organization_router_register(
    router,
    r"event/(?P<event_id>[^/]+)/image",
    EventImagesView,
    basename="Event-images",
)

organization_router_register(
    router,
    r"instruction",
    InstructionViewSet,
    basename="Instruction",
)

organization_router_register(
    router,
    r"instruction/(?P<instruction_id>[^/]+)/image",
    InstructionImagesView,
    basename="Instruction-images",
)
