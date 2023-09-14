from django.urls import path

from apps.healthcheck.views import liveness, readiness

urlpatterns = [
    path("live", liveness, name="liveness"),
    path("ready", readiness, name="readiness"),
]
