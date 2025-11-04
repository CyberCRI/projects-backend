from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.commons.urls import researcher_router_register
from services.crisalid.views import PublicationViewSet, ResearcherViewSet

researcher_router = DefaultRouter()
researcher_router.register(r"researcher", ResearcherViewSet, basename="Researcher")

researcher_router_register(
    researcher_router,
    r"publications",
    PublicationViewSet,
    basename="ResearcherPublications",
)

urlpatterns = [
    path("", include(researcher_router.urls)),
]
