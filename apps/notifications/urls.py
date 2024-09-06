from django.urls import include, path
from rest_framework.routers import SimpleRouter

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
]
