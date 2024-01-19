from types import SimpleNamespace

from apps.commons.pagination import PageInfoLimitOffsetPagination
from apps.commons.test import JwtAPITestCase
from apps.organizations.factories import OrganizationFactory
from apps.organizations.models import Organization


class PageInfoLimitOffsetPaginationTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        Organization.objects.bulk_create(OrganizationFactory.build_batch(5, faq=None))

    def test_first_page(self):
        pagination = PageInfoLimitOffsetPagination()
        request = SimpleNamespace(
            build_absolute_uri=lambda: "",
            query_params={
                pagination.limit_query_param: 2,
                pagination.offset_query_param: 0,
            },
        )
        data = pagination.paginate_queryset(Organization.objects.all(), request)
        response = pagination.get_paginated_response(data)

        self.assertEqual(response.data["total_page"], 3)
        self.assertEqual(response.data["current_page"], 1)
        self.assertEqual(response.data["next_page"], 2)
        self.assertEqual(response.data["previous_page"], None)

    def test_middle_page(self):
        pagination = PageInfoLimitOffsetPagination()
        request = SimpleNamespace(
            build_absolute_uri=lambda: "",
            query_params={
                pagination.limit_query_param: 2,
                pagination.offset_query_param: 2,
            },
        )
        data = pagination.paginate_queryset(Organization.objects.all(), request)
        response = pagination.get_paginated_response(data)

        self.assertEqual(response.data["total_page"], 3)
        self.assertEqual(response.data["current_page"], 2)
        self.assertEqual(response.data["next_page"], 3)
        self.assertEqual(response.data["previous_page"], 1)

    def test_last_page(self):
        pagination = PageInfoLimitOffsetPagination()
        request = SimpleNamespace(
            build_absolute_uri=lambda: "",
            query_params={
                pagination.limit_query_param: 2,
                pagination.offset_query_param: 4,
            },
        )
        data = pagination.paginate_queryset(Organization.objects.all(), request)
        response = pagination.get_paginated_response(data)

        self.assertEqual(response.data["total_page"], 3)
        self.assertEqual(response.data["current_page"], 3)
        self.assertEqual(response.data["next_page"], None)
        self.assertEqual(response.data["previous_page"], 2)
