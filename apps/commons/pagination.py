from collections import OrderedDict

from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from rest_framework.utils.urls import replace_query_param


class PageInfoLimitOffsetPagination(LimitOffsetPagination):
    """
    Behave the same as `LimitOffsetPagination` but add total, current,
    previous and next page to the response.
    """

    def get_current_page(self) -> int:
        return self.offset // self.limit + 1

    def get_total_page(self) -> int:
        return -(-self.count // self.limit)

    def get_next_page(self) -> int:
        current = self.get_current_page()
        return None if current == self.get_total_page() else current + 1

    def get_previous_page(self) -> int:
        current = self.get_current_page()
        return None if current == 1 else current - 1

    def get_last(self) -> str:
        url = self.request.build_absolute_uri()
        return replace_query_param(
            url, self.offset_query_param, (self.get_total_page() - 1) * self.limit
        )

    def get_first(self) -> str:
        url = self.request.build_absolute_uri()
        return replace_query_param(url, self.offset_query_param, 0)

    def get_paginated_response(self, data) -> Response:
        return Response(
            OrderedDict(
                [
                    ("count", self.count),
                    ("total_page", self.get_total_page()),
                    ("current_page", self.get_current_page()),
                    ("next", self.get_next_link()),
                    ("next_page", self.get_next_page()),
                    ("previous", self.get_previous_link()),
                    ("previous_page", self.get_previous_page()),
                    ("last", self.get_last()),
                    ("first", self.get_first()),
                    ("results", data),
                ]
            )
        )

    def get_paginated_response_schema(self, schema) -> dict:
        schema = super().get_paginated_response_schema(schema)
        schema["properties"].update(
            {
                "total_page": {
                    "type": "integer",
                    "example": 123,
                },
                "current_page": {
                    "type": "integer",
                    "example": 123,
                },
                "next_page": {
                    "type": "integer",
                    "example": 123,
                },
                "previous_page": {
                    "type": "integer",
                    "example": 123,
                },
                "last": {
                    "type": "string",
                    "nullable": False,
                    "format": "uri",
                    "example": "http://api.example.org/accounts/?{offset_param}=400&{limit_param}=100".format(
                        offset_param=self.offset_query_param,
                        limit_param=self.limit_query_param,
                    ),
                },
                "first": {
                    "type": "string",
                    "nullable": False,
                    "format": "uri",
                    "example": "http://api.example.org/accounts/?{offset_param}=0&{limit_param}=100".format(
                        offset_param=self.offset_query_param,
                        limit_param=self.limit_query_param,
                    ),
                },
            }
        )
        return schema
