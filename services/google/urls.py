from django.urls import path

from .views import GroupEmailAvailableView, OrgUnitsView, UserEmailAvailableView

urlpatterns = [
    path(
        "user-email-available/",
        UserEmailAvailableView.as_view(),
        name="GoogleUserEmailAvailable",
    ),
    path(
        "group-email-available/",
        GroupEmailAvailableView.as_view(),
        name="GoogleGroupEmailAvailable",
    ),
    path(
        "org-units/",
        OrgUnitsView.as_view(),
        name="GoogleOrgUnits",
    ),
]
