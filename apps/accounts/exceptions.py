from typing import Optional

from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    AuthenticationFailed,
    PermissionDenied,
    ValidationError,
)

# Authentication errors


class InvalidTokenError(AuthenticationFailed):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = _("Token contained no recognizable user identification")
    default_code = "invalid_token"


class InactiveUserError(AuthenticationFailed):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = _("User is inactive")
    default_code = "inactive_user"


class InvalidInvitationError(AuthenticationFailed):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = _("Invitation link not found or expired")
    default_code = "invalid_invitation"


class ExpiredTokenError(AuthenticationFailed):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = _("Access token has expired")
    default_code = "expired_token"


class TokenPrefixMissingError(AuthenticationFailed):
    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = _("Token prefix is missing")
    default_code = "token_prefix_missing"


# Permission denied errors


class FeaturedProjectPermissionDeniedError(PermissionDenied):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = _("You cannot add projects that you do not have access to")
    default_code = "featured_project_permission_denied"


class UserRolePermissionDeniedError(PermissionDenied):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = _("You do not have the permission to assign this role")
    default_code = "user_role_permission_denied"

    def __init__(self, role: Optional[str] = None):
        detail = (
            _(f"You do not have the permission to assign this role : {role}")
            if role
            else self.default_detail
        )
        super().__init__(detail=detail)


# Technical errors


class EmailTypeMissingError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _(
        "email_type query parameter is missing. Choices are : admin_created, invitation, reset_password"
    )
    default_code = "keycloak_email_type_missing"


class PermissionNotFoundError(APIException):
    status_code = status.HTTP_404_NOT_FOUND
    default_detail = _("Permission not found")
    default_code = "permission_not_found"


class KeycloakSyncError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("An error occurred while syncing with Keycloak")
    default_code = "keycloak_sync_error"

    def __init__(self, message: Optional[str] = None, code: Optional[int] = None):
        detail = (
            _(f"An error occurred while syncing with Keycloak : {message}")
            if message
            else self.default_detail
        )
        self.status_code = code if code else self.status_code
        super().__init__(detail=detail)


class GoogleSyncError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("An error occurred while syncing with Google")
    default_code = "google_sync_error"

    def __init__(self, message: Optional[str] = None, code: Optional[int] = None):
        detail = (
            _(f"An error occurred while syncing with Google : {message}")
            if message
            else self.default_detail
        )
        self.status_code = code if code else self.status_code
        super().__init__(detail=detail)


# Validation errors


class GroupOrganizationChangeError(ValidationError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("The organization of a group cannot be changed")
    default_code = "group_organization_change_error"


class RootGroupParentError(ValidationError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("The root group cannot have a parent group")
    default_code = "root_group_parent_error"


class NonRootGroupParentError(ValidationError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("A non-root group must have a parent group")
    default_code = "non_root_group_parent_error"


class ParentGroupOrganizationError(ValidationError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("The parent group must belong to the same organization")
    default_code = "parent_group_organization_error"


class GroupHierarchyLoopError(ValidationError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("You are trying to create a loop in the group's hierarchy")
    default_code = "group_hierarchy_loop_error"


class UserRoleAssignmentError(ValidationError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("You cannot assign this role to a user")
    default_code = "user_role_assignment_error"

    def __init__(self, role: Optional[str] = None):
        detail = (
            _(f"You cannot assign this role to a user : {role}")
            if role
            else self.default_detail
        )
        super().__init__(detail=detail)
