from django.urls import include, path
from rest_framework_nested import routers

from apps.accounts.views import (
    PeopleGroupHeaderView,
    PeopleGroupLogoView,
    PeopleGroupViewSet,
)
from apps.commons.urls import DetailOnlyNestedRouter
from apps.invitations.views import AccessRequestViewSet, InvitationViewSet

from .views import (
    OrganizationBannerView,
    OrganizationImagesView,
    OrganizationLogoView,
    OrganizationViewSet,
    ProjectCategoryBackgroundView,
    ProjectCategoryViewSet,
    TemplateImagesView,
)

categories_router = routers.DefaultRouter()
categories_router.register(r"category", ProjectCategoryViewSet, basename="Category")

categories_nested_router = routers.NestedSimpleRouter(
    categories_router, r"category", lookup="category"
)
categories_nested_router.register(
    r"background", ProjectCategoryBackgroundView, basename="Category-background"
)
categories_nested_router.register(
    r"template-image", TemplateImagesView, basename="Template-images"
)

organizations_router = routers.DefaultRouter()
organizations_router.register(
    r"organization", OrganizationViewSet, basename="Organization"
)

organizations_nested_router = routers.NestedSimpleRouter(
    organizations_router, r"organization", lookup="organization"
)
organizations_nested_router.register(
    r"banner", OrganizationBannerView, basename="Organization-banner"
)
organizations_nested_router.register(
    r"logo", OrganizationLogoView, basename="Organization-logo"
)
organizations_nested_router.register(
    r"image", OrganizationImagesView, basename="Organization-images"
)
organizations_nested_router.register(
    r"people-group", PeopleGroupViewSet, basename="PeopleGroup"
)
organizations_nested_router.register(
    r"invitation", InvitationViewSet, basename="Invitation"
)
organizations_nested_router.register(
    r"access-request", AccessRequestViewSet, basename="AccessRequest"
)

details_only_organizations_nested_router = DetailOnlyNestedRouter(
    organizations_router, r"organization", lookup="organization"
)

details_only_people_groups_nested_router = DetailOnlyNestedRouter(
    organizations_nested_router, r"people-group", lookup="people_group"
)
details_only_people_groups_nested_router.register(
    r"logo",
    PeopleGroupLogoView,
    basename="PeopleGroup-logo",
)
details_only_people_groups_nested_router.register(
    r"header",
    PeopleGroupHeaderView,
    basename="PeopleGroup-header",
)

urlpatterns = [
    path(r"", include(categories_router.urls)),
    path(r"", include(categories_nested_router.urls)),
    path(r"", include(organizations_router.urls)),
    path(r"", include(organizations_nested_router.urls)),
    path(r"", include(details_only_organizations_nested_router.urls)),
    path(r"", include(details_only_people_groups_nested_router.urls)),
]
