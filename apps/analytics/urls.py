from rest_framework_nested import routers

from .views import StatsViewSet

router = routers.SimpleRouter()
router.register(r"stats", StatsViewSet, basename="Stats")
