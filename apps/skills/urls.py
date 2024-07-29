from rest_framework.routers import DefaultRouter

from apps.commons.urls import organization_router_register, user_router_register

from .views import UserMentorshipViewset, OrganizationMentorshipViewset

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