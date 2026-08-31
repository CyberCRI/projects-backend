from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.accounts.views import (
    AccessTokenView,
    DeleteCookieView,
    PeopleGroupLocationViewSet,
    PrivacySettingsViewSet,
    UserFollowerCategoryViewSet,
    UserFollowerProjectViewSet,
    UserMemberProjectViewSet,
    UserProfilePictureView,
    UserReviewerProjectViewSet,
    UserViewSet,
)
from apps.commons.urls import (
    organization_people_group_router_register,
    user_router_register,
)
from apps.feedbacks.views import ReviewViewSet, UserFollowViewSet

router = DefaultRouter()
router.register(r"user", UserViewSet, basename="ProjectUser")
router.register(r"privacy-settings", PrivacySettingsViewSet, basename="PrivacySettings")

user_router_register(router, r"follow", UserFollowViewSet, basename="Follower")
user_router_register(router, r"review", ReviewViewSet, basename="Reviewer")

user_router_register(
    router,
    r"profile-picture",
    UserProfilePictureView,
    basename="UserProfilePicture",
)

user_router_register(
    router,
    r"projects/member",
    UserMemberProjectViewSet,
    basename="UserMemberProject",
)

user_router_register(
    router,
    r"projects/reviewer",
    UserReviewerProjectViewSet,
    basename="UserReviewerProject",
)

user_router_register(
    router,
    r"projects/follower",
    UserFollowerProjectViewSet,
    basename="UserFollowerProject",
)

user_router_register(
    router,
    r"categories/follower",
    UserFollowerCategoryViewSet,
    basename="UserFollowerCategory",
)

organization_people_group_router_register(
    router,
    r"locations",
    PeopleGroupLocationViewSet,
    basename="PeopleGroupLocations",
)

urlpatterns = [
    path("access-token/", AccessTokenView.as_view()),
    path("user/remove-authentication-cookie", DeleteCookieView.as_view()),
]
