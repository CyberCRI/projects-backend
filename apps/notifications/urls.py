from django.urls import include, path
from rest_framework.routers import SimpleRouter

from apps.projects.urls import nested_router as project_nested_router

from . import views

router = SimpleRouter()
router.register(r"report", views.ReportViewSet, basename="Report")
router.register(r"contact", views.ContactViewSet, basename="Contact")
router.register(r"notification", views.NotificationsViewSet, basename="Notification")
router.register(
    r"notifications-setting",
    views.NotificationSettingsViewSet,
    basename="NotificationSettings",
)

urlpatterns = [
    path(r"", include(router.urls)),
    path(r"", include(project_nested_router.urls)),
]
