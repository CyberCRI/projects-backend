from typing import Optional

from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError

# Permission denied errors


class CommentProjectPermissionDeniedError(PermissionDenied):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = _("You don't have the permission to comment on this project")
    default_code = "comment_project_permission_denied"

    def __init__(self, project_title: Optional[str] = None):
        detail = (
            _(
                "You don't have the permission to comment on this project : {project_title}"
            ).format(project_title=project_title)
            if project_title
            else self.default_detail
        )
        super().__init__(detail=detail)


class FollowProjectPermissionDeniedError(PermissionDenied):
    status_code = status.HTTP_403_FORBIDDEN
    default_detail = _("You don't have the permission to follow this project")
    default_code = "follow_project_permission_denied"

    def __init__(self, project_title: Optional[str] = None):
        detail = (
            _(
                "You don't have the permission to follow this project : {project_title}"
            ).format(project_title=project_title)
            if project_title
            else self.default_detail
        )
        super().__init__(detail=detail)


# Validation errors


class CommentReplyOnReplyError(ValidationError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("You cannot reply to a reply")
    default_code = "comment_reply_on_reply_error"


class CommentReplyToSelfError(ValidationError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("A comment cannot be a reply to itself")
    default_code = "comment_reply_to_self_error"
