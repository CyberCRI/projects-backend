from django.urls import include, path
from rest_framework_nested.routers import DefaultRouter, NestedSimpleRouter

from services.crisalid.views import DocumentViewSet, ResearcherViewSet

crisalid_router = DefaultRouter()
crisalid_router.register(r"researcher", ResearcherViewSet, basename="Researcher")

researcher_nested_router = NestedSimpleRouter(
    crisalid_router, r"researcher", lookup="researcher"
)

researcher_nested_router.register(
    r"documents", DocumentViewSet, basename="ResearcherDocuments"
)

urlpatterns = [
    path("", include(researcher_nested_router.urls)),
    path("", include(crisalid_router.urls)),
]
