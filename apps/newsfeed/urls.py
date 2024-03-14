from rest_framework_nested import routers

from . import views

router = routers.SimpleRouter()

router.register(r"newsfeed", views.NewsfeedViewSet, basename="Newsfeed")
