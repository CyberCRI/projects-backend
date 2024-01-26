from unittest.mock import patch

from django.urls import reverse
from faker import Faker

from apps.commons.test.testcases import JwtAPITestCase, TagTestCaseMixin

# from apps.misc.api import create_tag_from_wikipedia_gw
from apps.misc.models import WikipediaTag

faker = Faker()


class WikipediaTagTestCase(JwtAPITestCase, TagTestCaseMixin):
    @patch("apps.misc.api.get_query_from_wikipedia_gw")
    def test_api_func(self, mocked):
        mocked_response = self.query_wikipedia_mocked_return()
        mocked.return_value = mocked_response
        response = self.client.get(
            reverse("WikipediaTagWikipedia-list"), {"q": faker.word()}
        )
        assert response.status_code == mocked_response.status_code
        assert response.json() == mocked_response.json()

    @patch("apps.misc.api.get_tag_from_wikipedia_gw")
    def test_api_detail_func(self, mocked):
        wikipedia_qid = self.get_random_wikipedia_qid()
        mocked_response = self.get_wikipedia_tag_mocked_return(wikipedia_qid)
        mocked.return_value = mocked_response
        response = self.client.get(
            reverse("WikipediaTagWikipedia-detail", args=(wikipedia_qid,))
        )
        assert response.status_code == mocked_response.status_code
        assert response.json() == mocked_response.json()

    @patch("apps.misc.api.get_tag_from_wikipedia_gw")
    def test_api_detail_func_no_default(self, mocked):
        wikipedia_qid = self.get_random_wikipedia_qid()
        mocked.return_value = self.get_wikipedia_tag_mocked_return(
            wikipedia_qid, default=False
        )
        # create_tag_from_wikipedia_gw(wikipedia_qid)
        tag = WikipediaTag.objects.get(wikipedia_qid=wikipedia_qid)
        assert tag.name == tag.name_en == f"name_en_{wikipedia_qid}"
        assert tag.name_fr == f"name_fr_{wikipedia_qid}"

    @patch("apps.misc.api.get_tag_from_wikipedia_gw")
    def test_api_detail_func_no_default_no_en(self, mocked):
        wikipedia_qid = self.get_random_wikipedia_qid()
        mocked.return_value = self.get_wikipedia_tag_mocked_return(
            wikipedia_qid, default=False, en=False
        )
        # create_tag_from_wikipedia_gw(wikipedia_qid)
        tag = WikipediaTag.objects.get(wikipedia_qid=wikipedia_qid)
        assert tag.name == tag.name_fr == tag.name_en == f"name_fr_{wikipedia_qid}"
