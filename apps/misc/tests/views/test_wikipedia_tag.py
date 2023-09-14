from unittest.mock import patch

from django.urls import reverse

from apps.commons.test import JwtAPITestCase
from apps.misc.api import create_tag_from_wikipedia_gw
from apps.misc.models import WikipediaTag


class MockResponse:
    status_code = 200

    @staticmethod
    def json():
        return {
            "warnings": None,
            "fr": [
                {
                    "pageid": 6243370,
                    "ns": 0,
                    "title": "Breakout (chanson des Foo Fighters)",
                    "index": 1,
                    "pageprops": {"wikibase_item": "Q2706964"},
                    "links": [
                        {"ns": 0, "title": "18 septembre"},
                    ],
                    "extract": "Breakout est le quatrieme single de l'album There Is Nothing Left to Lose sorti en 2000.",
                }
            ],
        }


class MockResponseID:
    status_code = 200

    @staticmethod
    def json():
        return {
            "name_fr": "tag fr",
            "name_en": "tag en",
            "name": "tag default",
            "wikipedia_qid": "Q560361",
        }


class MockResponseNoName:
    status_code = 200

    @staticmethod
    def json():
        return {
            "name_fr": "tag fr",
            "name_en": "tag en",
            "name": "",
            "wikipedia_qid": "Q560361",
        }


class MockResponseNoNameEn:
    status_code = 200

    @staticmethod
    def json():
        return {
            "name_fr": "tag fr",
            "name_en": None,
            "name": "",
            "wikipedia_qid": "Q560361",
        }


class WikipediaTagTestCase(JwtAPITestCase):
    @patch(target="requests.get", return_value=MockResponse())
    def test_api_func(self, mocked):
        mocked_response = MockResponse()
        response = self.client.get(reverse("WikipediaTagWikipedia-list"), {"q": "foo"})
        assert response.status_code == mocked_response.status_code
        assert response.json() == mocked_response.json()

    @patch(target="requests.get", return_value=MockResponseID())
    def test_api_detail_func(self, mocked):
        mocked_response = MockResponseID()
        response = self.client.get(
            reverse("WikipediaTagWikipedia-detail", kwargs={"wikipedia_qid": "Q560361"})
        )
        assert response.status_code == mocked_response.status_code
        assert response.json() == mocked_response.json()

    @patch(target="requests.get", return_value=MockResponse())
    def test_api_disambiguation_func(self, mocked):
        mocked_response = MockResponse()
        response = self.client.get(
            reverse("WikipediaTagWikipedia-disambiguate", kwargs={"page_id": "123456"})
        )
        assert response.status_code == mocked_response.status_code
        assert response.json() == mocked_response.json()

    @patch(
        target="apps.misc.api.get_tag_from_wikipedia_gw",
        return_value=MockResponseNoName(),
    )
    def test_api_detail_func_no_default(self, mocked):
        create_tag_from_wikipedia_gw("Q560361")
        tag = WikipediaTag.objects.get(wikipedia_qid="Q560361")
        assert tag.name == "tag en"
        assert tag.name_fr == "tag fr"
        assert tag.name_en == "tag en"

    @patch(
        target="apps.misc.api.get_tag_from_wikipedia_gw",
        return_value=MockResponseNoNameEn(),
    )
    def test_api_detail_func_no_default_no_en(self, mocked):
        create_tag_from_wikipedia_gw("Q560361")
        tag = WikipediaTag.objects.get(wikipedia_qid="Q560361")
        assert tag.name == "tag fr"
        assert tag.name_fr == "tag fr"
        assert tag.name_en == "tag fr"
