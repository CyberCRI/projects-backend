from rest_framework.routers import DefaultRouter

from apps.announcements.views import AnnouncementViewSet
from apps.commons.urls import project_router_register
from apps.feedbacks.views import (
    CommentImagesView,
    CommentViewSet,
    ProjectFollowViewSet,
    ReviewViewSet,
)

from .views import (
    BlogEntryImagesView,
    BlogEntryViewSet,
    GoalViewSet,
    HistoricalProjectViewSet,
    LinkedProjectViewSet,
    LocationViewSet,
    ProjectHeaderView,
    ProjectImagesView,
    ProjectMessageImagesView,
    ProjectMessageViewSet,
    ProjectTabImagesView,
    ProjectTabItemImagesView,
    ProjectTabItemViewset,
    ProjectTabViewset,
    ProjectViewSet,
    ReadLocationViewSet,
)

router = DefaultRouter()
router.register(r"location", ReadLocationViewSet, basename="Read-location")
router.register(r"project", ProjectViewSet, basename="Project")

project_router_register(
    router,
    r"history",
    HistoricalProjectViewSet,
    basename="Project-versions",
)
project_router_register(router, r"blog-entry", BlogEntryViewSet, basename="BlogEntry")
project_router_register(
    router, r"blog-entry-image", BlogEntryImagesView, basename="BlogEntry-images"
)
project_router_register(router, r"location", LocationViewSet, basename="Location")
project_router_register(
    router, r"linked-project", LinkedProjectViewSet, basename="LinkedProjects"
)
project_router_register(router, r"goal", GoalViewSet, basename="Goal")
project_router_register(router, r"comment", CommentViewSet, basename="Comment")
project_router_register(
    router, r"comment-image", CommentImagesView, basename="Comment-images"
)
project_router_register(router, r"follow", ProjectFollowViewSet, basename="Followed")
project_router_register(router, r"review", ReviewViewSet, basename="Reviewed")
project_router_register(
    router, r"announcement", AnnouncementViewSet, basename="Announcement"
)
project_router_register(router, r"image", ProjectImagesView, basename="Project-images")
project_router_register(router, r"header", ProjectHeaderView, basename="Project-header")
project_router_register(
    router, r"project-message", ProjectMessageViewSet, basename="ProjectMessage"
)
project_router_register(
    router,
    r"project-message-image",
    ProjectMessageImagesView,
    basename="ProjectMessage-images",
)
project_router_register(router, r"tab", ProjectTabViewset, basename="ProjectTab")
project_router_register(
    router, r"tab-image", ProjectTabImagesView, basename="ProjectTab-images"
)
project_router_register(
    router,
    r"tab/(?P<tab_id>[^/]+)/item",
    ProjectTabItemViewset,
    basename="ProjectTabItem",
)
project_router_register(
    router,
    r"tab/(?P<tab_id>[^/]+)/item-image",
    ProjectTabItemImagesView,
    basename="ProjectTabItem-images",
)
