from apps.commons.urls import (
    organization_researcher_router_register,
    organization_router_register,
)
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from services.crisalid.views import (
    ConferenceViewSet,
    PublicationViewSet,
    ResearcherViewSet,
)

researcher_router = DefaultRouter()

organization_router_register(r"researcher", ResearcherViewSet, basename="Researcher")

organization_researcher_router_register(
    researcher_router,
    r"publications",
    PublicationViewSet,
    basename="ResearcherPublications",
)

organization_researcher_router_register(
    researcher_router,
    r"conferences",
    ConferenceViewSet,
    basename="ResearcherConferences",
)

urlpatterns = [
    path("", include(researcher_router.urls)),
]
