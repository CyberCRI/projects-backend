from rest_framework_nested.routers import DefaultRouter

from .views import SearchViewSet

router = DefaultRouter()

router.register(r"search", SearchViewSet, basename="Search")
