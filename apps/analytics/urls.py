from rest_framework_nested import routers
from apps.commons.urls import organization_router_register

from .views import StatsViewSet

router = routers.SimpleRouter()

organization_router_register(
    router,
    r"stats",
    StatsViewSet,
    basename="Stats",
)
