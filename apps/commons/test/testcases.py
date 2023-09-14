import logging

from django.test import SimpleTestCase
from rest_framework.test import (
    APILiveServerTestCase,
    APISimpleTestCase,
    APITestCase,
    APITransactionTestCase,
)

from .client import JwtClient
from .mixins import GetImageTestCaseMixin


class JwtTestCaseMixin(
    SimpleTestCase,
    GetImageTestCaseMixin,
):
    """Modify the default client to use JwtClient."""

    client: JwtClient

    client_class = JwtClient

    @classmethod
    def setUpClass(cls):
        """Disable logging while testing."""
        super().setUpClass()
        logging.disable(logging.CRITICAL)

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()  # noqa
        cls.test_image = cls.get_test_image()

    @classmethod
    def tearDownClass(cls):
        """Re-enable logging after testing."""
        super().tearDownClass()
        logging.disable(logging.NOTSET)

    def tearDown(self):
        """Logout any authentication at the end of each test."""
        super().tearDown()
        self.client.logout()
        self.client.credentials()


class JwtAPISimpleTestCase(JwtTestCaseMixin, APISimpleTestCase):
    """`APISimpleTestCase` using `JwtClient`."""

    pass


class JwtAPITransactionTestCase(JwtTestCaseMixin, APITransactionTestCase):
    """`APITransactionTestCase` using `JwtClient`."""

    pass


class JwtAPITestCase(JwtTestCaseMixin, APITestCase):
    """`APITestCase` using `JwtClient`."""


class JwtAPILiveServerTestCase(JwtTestCaseMixin, APILiveServerTestCase):
    """`APILiveServerTestCase` using `JwtClient`."""

    pass


class TagTestCase:
    class MockResponse:
        def __init__(self, **kwargs):
            self.dict = kwargs.pop("dict", {})

        def json(self):
            return self.dict

    def side_effect(self, qid, *args, **kwargs):
        results = {
            "Q1735684": {
                "name_en": "Kate Foo Kune en",
                "name_fr": "Kate Foo Kune fr",
                "name": "Kate Foo Kune default",
                "wikipedia_qid": "Q1735684",
            },
            "Q12335103": {
                "name_en": "Sharin Foo en",
                "name_fr": "Sharin Foo fr",
                "name": "Sharin Foo default",
                "wikipedia_qid": "Q12335103",
            },
            "Q3737270": {
                "name_en": "FOO en",
                "name_fr": "FOO fr",
                "name": "FOO default",
                "wikipedia_qid": "Q3737270",
            },
            "Q560361": {
                "name_fr": "brouillon",
                "name_en": "draft document",
                "name": "draft document",
                "wikipedia_qid": "Q560361",
            },
        }
        return self.MockResponse(dict=results[qid])
