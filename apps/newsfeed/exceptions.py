from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.exceptions import ValidationError


class NewsPeopleGroupOrganizationError(ValidationError):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _(
        "The people groups of a news must belong to the same organization"
    )
    default_code = "news_people_group_organization_error"
