from rest_framework.routers import DefaultRouter

from apps.announcements import views

router = DefaultRouter()
router.register(
    r"announcement", views.ReadAnnouncementViewSet, basename="Read-announcement"
)
