from rest_framework.routers import DefaultRouter

from apps.commons.urls import (
    organization_people_group_router_register,
    organization_router_register,
    project_router_register,
    user_router_register,
)
from apps.files.views import (
    AttachmentFileViewSet,
    AttachmentLinkViewSet,
    OrganizationAttachmentFileViewSet,
    PeopleGroupGalleryViewSet,
    ProjectUserAttachmentFileViewSet,
    ProjectUserAttachmentLinkViewSet,
)

router = DefaultRouter()

organization_router_register(
    router,
    r"file",
    OrganizationAttachmentFileViewSet,
    basename="OrganizationAttachmentFile",
)
project_router_register(
    router,
    r"file",
    AttachmentFileViewSet,
    basename="AttachmentFile",
)
project_router_register(
    router, r"link", AttachmentLinkViewSet, basename="AttachmentLink"
)


user_router_register(
    router,
    r"file",
    ProjectUserAttachmentFileViewSet,
    basename="ProjectUserAttachmentFile",
)
user_router_register(
    router,
    r"link",
    ProjectUserAttachmentLinkViewSet,
    basename="ProjectUserAttachmentLink",
)

organization_people_group_router_register(
    router, r"gallery", PeopleGroupGalleryViewSet, basename="PeopleGroupGallery"
)
