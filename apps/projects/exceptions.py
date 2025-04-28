from typing import List, Optional

from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.exceptions import APIException, PermissionDenied, ValidationError

# Permission denied errors


class LinkedProjectPermissionDeniedError(PermissionDenied):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = _("You don't have the permission to link this project")
    default_code = "linked_project_permission_denied"

    def __init__(self, project_title: Optional[str] = None):
        detail = (
            _(f"You don't have the permission to link this project : {project_title}")
            if project_title
            else self.default_detail
        )
        super().__init__(detail=detail)


class AddProjectToOrganizationPermissionError(PermissionDenied):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = _(
        "You do not have the rights to add a project in this organization"
    )
    default_code = "add_project_to_organization_permission_error"


class LockedProjectError(PermissionDenied):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = _("You cannot modify a locked project")
    default_code = "locked_project_error"


# Technical errors


class OrganizationsParameterMissing(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("The organizations parameter is mandatory")
    default_code = "organizations_parameter_missing_error"


class WrongProjectOrganizationError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("The project does not belong to any of the given organizations")
    default_code = "wrong_project_organization_error"

    def __init__(
        self,
        project_title: Optional[str] = None,
        organizations_names: Optional[List[str]] = None,
    ):
        detail = (
            f"The project '{project_title}' does not belong to any of the given organizations: {' ,'.join(organizations_names)}"
            if project_title and organizations_names
            else self.default_detail
        )
        super().__init__(detail=detail)


# Validation errors


class RemoveLastProjectOwnerError(ValidationError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("You cannot remove all the owners of a project")
    default_code = "remove_last_project_owner_error"


class ProjectWithNoOrganizationError(ValidationError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("A project must belong to at least one organization")
    default_code = "project_with_no_organization_error"


class OnlyReviewerCanChangeStatusError(ValidationError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("Only a reviewer can change this project's status")
    default_code = "only_reviewer_can_change_status_error"


class EmptyProjectDescriptionError(ValidationError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("You cannot empty the description of a project")
    default_code = "empty_project_description_error"


class ProjectCategoryOrganizationError(ValidationError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _(
        "A project cannot be in a category if it doesn't belong to one of the project's organizations"
    )
    default_code = "project_category_organization_error"


class LinkProjectToSelfError(ValidationError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("A project can't be linked to itself")
    default_code = "link_project_to_self_error"

    def __init__(self, project_title: Optional[str] = None):
        detail = (
            _(f"The project '{project_title}' can't be linked to itself")
            if project_title
            else self.default_detail
        )
        super().__init__(detail={"project_id": [detail]})


class ProjectMessageReplyOnReplyError(ValidationError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("You cannot reply to a reply")
    default_code = "project_message_reply_on_reply_error"


class ProjectMessageReplyToSelfError(ValidationError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("A message cannot be a reply to itself")
    default_code = "project_message_reply_to_self_error"


class ProjectTabChangeTypeError(ValidationError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("You cannot change the type of a project's tab")
    default_code = "project_tab_change_type_error"
