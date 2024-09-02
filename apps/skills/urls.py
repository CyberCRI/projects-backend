from rest_framework.routers import DefaultRouter

from apps.commons.urls import organization_router_register, user_router_register

from .views import (
    MentorshipContactViewset,
    OrganizationMentorshipViewset,
    UserMentorshipViewset,
)

router = DefaultRouter()

organization_router_register(
    router,
    r"",
    OrganizationMentorshipViewset,
    basename="OrganizationMentorship",
)

user_router_register(
    router,
    r"",
    UserMentorshipViewset,
    basename="UserMentorship",
)

organization_router_register(
    router,
    r"skill/(?P<skill_id>\d+)",
    MentorshipContactViewset,
    basename="MentorshipContact",
)
