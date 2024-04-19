from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError

# Validation errors


class OrganizationHierarchyLoopError(ValidationError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _(
        "You are trying to create a loop in the organization's hierarchy."
    )
    default_code = "organization_hierarchy_loop_error"


class FeaturedProjectPermissionDeniedError(PermissionDenied):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = _("You cannot add projects that you do not have access to")
    default_code = "featured_project_permission_denied"
