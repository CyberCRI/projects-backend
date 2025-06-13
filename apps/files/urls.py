from rest_framework_nested.routers import SimpleRouter

from apps.commons.urls import organization_router_register, project_router_register
from apps.files.views import (
    AttachmentFileViewSet,
    AttachmentLinkViewSet,
    OrganizationAttachmentFileViewSet,
)

router = SimpleRouter()

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
