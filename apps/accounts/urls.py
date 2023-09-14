from django.urls import include, path
from rest_framework_nested.routers import DefaultRouter, NestedSimpleRouter

from apps.accounts.views import (
    DeleteCookieView,
    PrivacySettingsViewSet,
    SkillViewSet,
    UserProfilePictureView,
    UserViewSet,
)
from apps.feedbacks.views import ReviewViewSet, UserFollowViewSet

router = DefaultRouter()
router.register(r"skill", SkillViewSet, basename="Skill")
router.register(r"privacy-settings", PrivacySettingsViewSet, basename="PrivacySettings")

user_router = DefaultRouter()
user_router.register(r"user", UserViewSet, basename="ProjectUser")

nested_router = NestedSimpleRouter(user_router, r"user", lookup="user")
nested_router.register(r"follow", UserFollowViewSet, basename="Follower")
nested_router.register(r"review", ReviewViewSet, basename="Reviewer")
nested_router.register(
    r"profile-picture", UserProfilePictureView, basename="UserProfilePicture"
)

urlpatterns = [
    path("", include(user_router.urls)),
    path("", include(nested_router.urls)),
    path(
        "user/remove-authentication-cookie",
        DeleteCookieView.as_view(),
        name="remove-authentication-cookie",
    ),
]
