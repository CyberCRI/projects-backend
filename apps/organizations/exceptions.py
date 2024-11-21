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


class RootCategoryParentError(ValidationError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("The root category cannot have a parent category")
    default_code = "root_category_parent_error"


class NonRootCategoryParentError(ValidationError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("A non-root category must have a parent category")
    default_code = "non_root_category_parent_error"


class ParentCategoryOrganizationError(ValidationError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("The parent category must belong to the same organization")
    default_code = "parent_category_organization_error"


class CategoryHierarchyLoopError(ValidationError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("You are trying to create a loop in the category's hierarchy")
    default_code = "category_hierarchy_loop_error"


class DefaultTagClassificationIsNotEnabledError(ValidationError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("You must choose a default tag classification that is enabled")
    default_code = "default_tag_classification_is_not_enabled_error"
