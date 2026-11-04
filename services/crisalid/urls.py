from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.commons.urls import (
    organization_people_group_router_register,
    organization_researcher_router_register,
    organization_router_register,
)
from services.crisalid.views import (
    AwardViewSet,
    ConferenceViewSet,
    DocumentViewSet,
    FundingViewSet,
    GroupConferenceViewSet,
    GroupPublicationViewSet,
    PatentViewSet,
    PublicationViewSet,
    ResearcherViewSet,
    TeachingViewSet,
)

researcher_router = DefaultRouter()

organization_router_register(
    researcher_router, r"researcher", ResearcherViewSet, basename="Researcher"
)

organization_router_register(
    researcher_router, r"document", DocumentViewSet, basename="CrisalidDocument"
)

organization_router_register(
    researcher_router, r"award", AwardViewSet, basename="CrisalidAward"
)
organization_router_register(
    researcher_router, r"patent", PatentViewSet, basename="CrisalidPatent"
)

organization_router_register(
    researcher_router, r"teaching", TeachingViewSet, basename="CrisalidTeaching"
)
organization_router_register(
    researcher_router, r"funding", FundingViewSet, basename="CrisalidFunding"
)

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

# -- group
organization_people_group_router_register(
    researcher_router,
    r"publications",
    GroupPublicationViewSet,
    basename="GroupResearcherPublications",
)

organization_people_group_router_register(
    researcher_router,
    r"conferences",
    GroupConferenceViewSet,
    basename="GroupResearcherConferences",
)

urlpatterns = [path("", include(researcher_router.urls))]
