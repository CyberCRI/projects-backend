from rest_framework.routers import SimpleRouter

from apps.commons.urls import organization_router_register

from .views import (
    ContactViewSet,
    NotificationSettingsViewSet,
    NotificationsViewSet,
    ReportViewSet,
)

router = SimpleRouter()

router.register(r"notification", NotificationsViewSet, basename="Notification")
router.register(
    r"notifications-setting",
    NotificationSettingsViewSet,
    basename="NotificationSettings",
)
organization_router_register(
    router,
    r"report",
    ReportViewSet,
    basename="Report",
)
organization_router_register(
    router,
    r"contact",
    ContactViewSet,
    basename="Contact",
)
