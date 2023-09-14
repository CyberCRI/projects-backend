from django.urls import include, path
from rest_framework_nested import routers

from . import views

emails_router = routers.DefaultRouter()
emails_router.register(r"email", views.EmailViewSet, basename="Email")

nested_router = routers.NestedSimpleRouter(emails_router, r"email", lookup="email")
nested_router.register(r"image", views.EmailImagesViewSet, basename="Email-images")

urlpatterns = [
    path(r"", include(nested_router.urls)),
    path(r"", include(emails_router.urls)),
]
