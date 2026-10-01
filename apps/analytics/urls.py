from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.commons.urls import organization_router_register

from .views import GlobalAnalyticsView, StatsViewSet

router = DefaultRouter()

organization_router_register(router, r"stats", StatsViewSet, basename="Stats")

urlpatterns = [
    path("global-stats/", GlobalAnalyticsView.as_view(), name="GlobalStats"),
]
