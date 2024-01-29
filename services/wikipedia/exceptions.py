from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import APIException


class WikibaseAPIException(APIException):
    status_code = 400
    default_code = "wikibase_api_error"

    def __init__(self, status_code: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.default_detail = _(f"Wikipedia API returned {status_code}")
