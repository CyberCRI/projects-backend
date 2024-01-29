from unittest.mock import patch

from django.urls import reverse
from faker import Faker

from apps.commons.test.testcases import JwtAPITestCase, TagTestCaseMixin

faker = Faker()


class WikipediaServiceTestCase(JwtAPITestCase, TagTestCaseMixin):
    @patch("services.wikipedia.interface.WikipediaService.wbsearchentities")
    def test_search_tags(self, mocked):
        mocked.side_effect = self.search_wikipedia_tag_mocked_side_effect
        response = self.client.get(
            reverse("WikibaseItem-list"), {"query": faker.word()}
        )
        assert response.status_code == 200
        content = response.json()["results"]
        assert len(content) == 100
        result = content[0]
        assert all(key in result for key in ["wikipedia_qid", "name", "description"])

    @patch("services.wikipedia.interface.WikipediaService.wbgetentities")
    def test_search_tags_pagination(self, mocked):
        mocked.side_effect = self.search_wikipedia_tag_mocked_side_effect
        response = self.client.get(
            reverse("WikibaseItem-list"), {"query": faker.word(), "limit": 10}
        )
        assert response.status_code == 200
        content = response.json()
        assert "limit=10" in content["next"]
        assert "offset=10" in content["next"]
        assert len(content["results"]) == 10

    @patch("services.wikipedia.interface.WikipediaService.autocomplete")
    def test_autocomplete_default_limit(self, mocked):
        query = faker.word()
        mocked.side_effect = self.autocomplete_wikipedia_mocked_side_effect
        response = self.client.get(
            reverse("WikibaseItem-autocomplete"), {"query": query}
        )
        assert response.status_code == 200
        content = response.json()
        assert len(content) == 5
        assert all(item.startswith(query) for item in content)

    @patch("services.wikipedia.interface.WikipediaService.autocomplete")
    def test_autocomplete_custom_limit(self, mocked):
        query = faker.word()
        mocked.side_effect = self.autocomplete_wikipedia_mocked_side_effect
        response = self.client.get(
            reverse("WikibaseItem-autocomplete"), {"query": query, "limit": 10}
        )
        assert response.status_code == 200
        content = response.json()
        assert len(content) == 10
        assert all(item.startswith(query) for item in content)
