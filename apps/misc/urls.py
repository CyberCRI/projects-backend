from rest_framework.routers import DefaultRouter

from .views import TagViewSet, WikipediaTagViewSet

router = DefaultRouter()
router.register("wikipedia-tag", WikipediaTagViewSet, basename="WikipediaTag")
router.register("tag", TagViewSet, basename="Tag")
