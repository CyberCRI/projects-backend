from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.exceptions import ValidationError

# Validation errors


class OrganizationHierarchyLoopError(ValidationError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _(
        "You are trying to create a loop in the organization's hierarchy."
    )
    default_code = "organization_hierarchy_loop_error"
