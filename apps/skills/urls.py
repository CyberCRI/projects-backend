from rest_framework.routers import DefaultRouter

from apps.commons.urls import (
    organization_router_register,
    organization_user_router_register,
    user_router_register,
)

from .views import (
    MentorshipContactViewset,
    OrganizationMentorshipViewset,
    SkillViewSet,
    TagViewSet,
    UserMentorshipViewset,
)

router = DefaultRouter()

organization_router_register(
    router,
    r"tag",
    TagViewSet,
    basename="OrganizationTag",
)

organization_router_register(
    router,
    r"tag-classification/(?P<tag_classification_id>\d+)/tag",
    TagViewSet,
    basename="ClassificationTag",
)

user_router_register(router, r"skill", SkillViewSet, basename="Skill")

organization_router_register(
    router,
    r"",
    OrganizationMentorshipViewset,
    basename="OrganizationMentorship",
)

organization_user_router_register(
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
