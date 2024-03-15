from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.exceptions import APIException

# Technical errors


class VectorSearchWrongQuerysetError(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("The given queryset does not match the related model")
    default_code = "vector_search_wrong_queryset_error"
