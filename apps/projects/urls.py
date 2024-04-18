from django.urls import include, path
from rest_framework_nested import routers

from apps.announcements.views import AnnouncementViewSet
from apps.feedbacks.views import (
    CommentImagesView,
    CommentViewSet,
    ProjectFollowViewSet,
    ReviewViewSet,
)
from apps.files.views import AttachmentFileViewSet, AttachmentLinkViewSet
from apps.goals.views import GoalViewSet

from . import views

router = routers.SimpleRouter()

router.register(r"location", views.ReadLocationViewSet, basename="Read-location")

projects_router = routers.DefaultRouter()
projects_router.register(r"project", views.ProjectViewSet, basename="Project")

nested_router = routers.NestedSimpleRouter(
    projects_router, r"project", lookup="project"
)
nested_router.register(
    r"history", views.HistoricalProjectViewSet, basename="Project-versions"
)
nested_router.register(r"file", AttachmentFileViewSet, basename="AttachmentFile")
nested_router.register(r"link", AttachmentLinkViewSet, basename="AttachmentLink")
nested_router.register(r"blog-entry", views.BlogEntryViewSet, basename="BlogEntry")
nested_router.register(
    r"blog-entry-image", views.BlogEntryImagesView, basename="BlogEntry-images"
)
nested_router.register(r"location", views.LocationViewSet, basename="Location")
nested_router.register(
    r"linked-project", views.LinkedProjectViewSet, basename="LinkedProjects"
)
nested_router.register(r"goal", GoalViewSet, basename="Goal")
nested_router.register(r"comment", CommentViewSet, basename="Comment")
nested_router.register(r"comment-image", CommentImagesView, basename="Comment-images")
nested_router.register(r"follow", ProjectFollowViewSet, basename="Followed")
nested_router.register(r"review", ReviewViewSet, basename="Reviewed")
nested_router.register(r"announcement", AnnouncementViewSet, basename="Announcement")
nested_router.register(r"image", views.ProjectImagesView, basename="Project-images")
nested_router.register(r"header", views.ProjectHeaderView, basename="Project-header")

urlpatterns = [
    path(r"", include(nested_router.urls)),
    path(r"", include(projects_router.urls)),
]
