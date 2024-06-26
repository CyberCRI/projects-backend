from django.urls import include, path
from rest_framework_nested.routers import DefaultRouter

from apps.accounts.views import (
    DeleteCookieView,
    PrivacySettingsViewSet,
    SkillViewSet,
    UserProfilePictureView,
    UserViewSet,
)
from apps.commons.urls import organization_router_register, user_router_register
from apps.feedbacks.views import ReviewViewSet, UserFollowViewSet

router = DefaultRouter()
user_router_register(
    router,
    r"skill",
    SkillViewSet,
    basename="Skill",
)
organization_router_register(
    router,
    r"privacy-settings",
    PrivacySettingsViewSet,
    basename="PrivacySettings",
)
user_router_register(
    router,
    r"profile-picture",
    UserProfilePictureView,
    basename="ProfilePicture",
)
user_router_register(
    router,
    r"follow",
    UserFollowViewSet,
    basename="Follower",
)
user_router_register(
    router,
    r"review",
    ReviewViewSet,
    basename="Reviewer",
)

organization_router_register(
    router,
    r"user",
    UserViewSet,
    basename="ProjectUser",
)

urlpatterns = [
    path("", include(router.urls)),
    path(
        "user/remove-authentication-cookie",
        DeleteCookieView.as_view(),
        name="remove-authentication-cookie",
    ),
]
