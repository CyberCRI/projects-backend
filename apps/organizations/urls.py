from rest_framework.routers import DefaultRouter

from apps.accounts.views import (
    PeopleGroupHeaderView,
    PeopleGroupLogoView,
    PeopleGroupViewSet,
)
from apps.commons.urls import (
    OneToOneRouter,
    organization_router_register,
    people_group_router_register,
)
from apps.invitations.views import AccessRequestViewSet, InvitationViewSet

from .views import (
    OrganizationBannerView,
    OrganizationImagesView,
    OrganizationLogoView,
    OrganizationViewSet,
    ProjectCategoryBackgroundView,
    ProjectCategoryViewSet,
    TemplateImagesView,
    TemplateViewSet,
    TermsAndConditionsViewSet,
)

router = DefaultRouter()
router.register(r"organization", OrganizationViewSet, basename="Organization")
organization_router_register(
    router, r"people-group", PeopleGroupViewSet, basename="PeopleGroup"
)
organization_router_register(
    router, r"category", ProjectCategoryViewSet, basename="Category"
)
organization_router_register(router, r"template", TemplateViewSet, basename="Template")
organization_router_register(
    router,
    r"category/(?P<category_id>[^/]+)/background",
    ProjectCategoryBackgroundView,
    basename="Category-background",
)
organization_router_register(
    router,
    r"template/(?P<template_id>[^/]+)/image",
    TemplateImagesView,
    basename="Template-images",
)
organization_router_register(
    router, r"banner", OrganizationBannerView, basename="Organization-banner"
)
organization_router_register(
    router, r"logo", OrganizationLogoView, basename="Organization-logo"
)
organization_router_register(
    router, r"image", OrganizationImagesView, basename="Organization-images"
)
organization_router_register(
    router, r"invitation", InvitationViewSet, basename="Invitation"
)
organization_router_register(
    router, r"access-request", AccessRequestViewSet, basename="AccessRequest"
)
organization_router_register(
    router,
    r"terms-and-conditions",
    TermsAndConditionsViewSet,
    basename="TermsAndConditions",
)

one_to_one_router = OneToOneRouter()
people_group_router_register(
    one_to_one_router, r"logo", PeopleGroupLogoView, basename="PeopleGroup-logo"
)
people_group_router_register(
    one_to_one_router, r"header", PeopleGroupHeaderView, basename="PeopleGroup-header"
)
