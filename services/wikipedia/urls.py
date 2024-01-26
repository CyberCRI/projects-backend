from rest_framework.routers import DefaultRouter

from .views import WikibaseItemViewset

router = DefaultRouter()
router.register(
    r"wikibase-item",
    WikibaseItemViewset,
    basename="WikibaseItem",
)