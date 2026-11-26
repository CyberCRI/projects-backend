from rest_framework.routers import DefaultRouter

from apps.commons.urls import organization_router_register

from .views import SearchViewSet

router = DefaultRouter()

organization_router_register(router, r"search", SearchViewSet, basename="Search")
