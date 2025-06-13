from rest_framework.routers import DefaultRouter

from apps.commons.urls import organization_router_register, project_router_register
from apps.files.views import (
    AttachmentFileViewSet,
    AttachmentLinkViewSet,
    OrganizationAttachmentFileViewSet,
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
