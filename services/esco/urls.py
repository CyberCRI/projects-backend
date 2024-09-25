from rest_framework.routers import DefaultRouter

from .views import EscoTagViewSet

router = DefaultRouter()

router.register(
    r"esco-tag",
    EscoTagViewSet,
    basename="EscoTag",
)
