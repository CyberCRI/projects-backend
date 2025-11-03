from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"email", views.EmailViewSet, basename="Email")
router.register(
    r"email/(?P<email_id>[^/]+)/image",
    views.EmailImagesViewSet,
    basename="Email-images",
)
