from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import APIException


class OrganizationsParameterMissing(APIException):
    status_code = 400
    default_detail = _("Organizations parameter is mandatory.")
    default_code = "organizations_parameter_missing"
