"""projects URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.shortcuts import redirect
from django.urls import include, path, reverse
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from apps.accounts.urls import router as accounts_router
from apps.analytics.urls import router as analytics_router
from apps.announcements.urls import router as announcements_router
from apps.commons.urls import ExtendedRouter, OneToOneExtendedRouter
from apps.files.urls import router as files_router
from apps.emailing.urls import router as emailing_router
from apps.newsfeed.urls import router as newsfeed_router
from apps.notifications.urls import router as notifications_router
from apps.organizations.urls import one_to_one_router as organizations_one_to_one_router
from apps.organizations.urls import router as organizations_router
from apps.organizations.views import AvailableLanguagesView
from apps.projects.urls import router as projects_router
from apps.search.urls import router as search_router
from apps.skills.urls import router as skills_router
from services.mistral.urls import mistral_router


def redirect_to_swagger(request):
    return redirect(reverse("swagger-ui"))


router = ExtendedRouter()

router.extend(
    accounts_router,
    analytics_router,
    announcements_router,
    emailing_router,
    files_router,
    newsfeed_router,
    notifications_router,
    organizations_router,
    projects_router,
    search_router,
    skills_router,
    mistral_router,
)

one_to_one_router = OneToOneExtendedRouter()
one_to_one_router.extend(
    organizations_one_to_one_router,
)

api_urlpatterns = [
    # Router based urls for ViewSets
    path("", include(router.urls)),
    path("", include(one_to_one_router.urls)),
    # urlpatterns based urls for function based views and APIViews
    path("", include("apps.accounts.urls")),
    path("google/", include("services.google.urls")),
    path("healthz/", include(("apps.healthcheck.urls", "healthcheck"))),
    path("languages/", AvailableLanguagesView.as_view(), name="Languages"),
    path("", include("django_prometheus.urls")),
]

spectacular_urlpatterns = [
    path("", SpectacularAPIView.as_view(), name="schema"),
    path("swagger-ui", SpectacularSwaggerView.as_view(), name="swagger-ui"),
    path("redoc", SpectacularRedocView.as_view(), name="redoc"),
]

urlpatterns = [
    path("", redirect_to_swagger, name="redirect-swagger"),
    path("v1/", include(api_urlpatterns)),
    path("admin/", admin.site.urls),
    path("api/schema/", include(spectacular_urlpatterns)),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

if settings.DEBUG and settings.DEBUG_TOOLBAR_INSTALLED:
    urlpatterns.insert(0, path("__debug__/", include("debug_toolbar.urls")))
