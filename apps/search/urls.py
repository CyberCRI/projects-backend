from rest_framework.routers import DefaultRouter

from .views import SearchViewSet

router = DefaultRouter()

router.register(r"search", SearchViewSet, basename="Search")
