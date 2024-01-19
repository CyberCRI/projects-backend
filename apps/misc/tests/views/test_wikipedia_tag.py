from unittest.mock import patch

from django.urls import reverse

from apps.commons.test import JwtAPITestCase
from apps.misc.api import create_tag_from_wikipedia_gw
from apps.misc.models import WikipediaTag


class WikipediaTagTestCase(JwtAPITestCase):
    class WikipediaMockResponse:
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

    class ProjectsMockResponse:
        status_code = 200

        def __init__(self, wikipedia_qid, name, name_fr, name_en):
            self.wikipedia_qid = wikipedia_qid
            self.name = name
            self.name_fr = name_fr
            self.name_en = name_en

        def json(self):
            return {
                "name_fr": self.name_fr,
                "name_en": self.name_en,
                "name": self.name,
                "wikipedia_qid": self.wikipedia_qid,
            }

    @patch(target="apps.misc.api.get_query_from_wikipedia_gw")
    def test_api_func(self, mocked):
        mocked_response = self.WikipediaMockResponse()
        mocked.return_value = mocked_response
        response = self.client.get(reverse("WikipediaTagWikipedia-list"), {"q": "foo"})
        assert response.status_code == mocked_response.status_code
        assert response.json() == mocked_response.json()

    @patch(target="apps.misc.api.get_tag_from_wikipedia_gw")
    def test_api_detail_func(self, mocked):
        mocked_response = self.ProjectsMockResponse(
            "Q560361", "tag default", "tag fr", "tag en"
        )
        mocked.return_value = mocked_response
        response = self.client.get(
            reverse("WikipediaTagWikipedia-detail", kwargs={"wikipedia_qid": "Q560361"})
        )
        assert response.status_code == mocked_response.status_code
        assert response.json() == mocked_response.json()

    @patch(target="apps.misc.api.get_disambiguation_page_from_wikipedia_gw")
    def test_api_disambiguation_func(self, mocked):
        mocked_response = self.WikipediaMockResponse()
        mocked.return_value = mocked_response
        response = self.client.get(
            reverse("WikipediaTagWikipedia-disambiguate", kwargs={"page_id": "123456"})
        )
        assert response.status_code == mocked_response.status_code
        assert response.json() == mocked_response.json()

    @patch("apps.misc.api.get_tag_from_wikipedia_gw")
    def test_api_detail_func_no_default(self, mocked):
        mocked.return_value = self.ProjectsMockResponse(
            "Q560361", "", "tag fr", "tag en"
        )
        create_tag_from_wikipedia_gw("Q560361")
        tag = WikipediaTag.objects.get(wikipedia_qid="Q560361")
        assert tag.name == "tag en"
        assert tag.name_fr == "tag fr"
        assert tag.name_en == "tag en"

    @patch("apps.misc.api.get_tag_from_wikipedia_gw")
    def test_api_detail_func_no_default_no_en(self, mocked):
        mocked.return_value = self.ProjectsMockResponse("Q560361", "", "tag fr", None)
        create_tag_from_wikipedia_gw("Q560361")
        tag = WikipediaTag.objects.get(wikipedia_qid="Q560361")
        assert tag.name == "tag fr"
        assert tag.name_fr == "tag fr"
        assert tag.name_en == "tag fr"
