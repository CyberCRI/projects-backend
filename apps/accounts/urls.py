from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.accounts.views import (
    AccessTokenView,
    DeleteCookieView,
    PrivacySettingsViewSet,
    UserProfilePictureView,
    UserViewSet,
)
from apps.commons.urls import user_router_register
from apps.feedbacks.views import ReviewViewSet, UserFollowViewSet

router = DefaultRouter()
router.register(r"user", UserViewSet, basename="ProjectUser")
router.register(r"privacy-settings", PrivacySettingsViewSet, basename="PrivacySettings")

user_router_register(router, r"follow", UserFollowViewSet, basename="Follower")
user_router_register(router, r"review", ReviewViewSet, basename="Reviewer")
user_router_register(
    router, r"profile-picture", UserProfilePictureView, basename="UserProfilePicture"
)


urlpatterns = [
    path("access-token/", AccessTokenView.as_view()),
    path("user/remove-authentication-cookie", DeleteCookieView.as_view()),
]
