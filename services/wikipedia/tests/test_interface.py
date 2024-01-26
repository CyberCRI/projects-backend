from unittest.mock import patch

from faker import Faker

from apps.commons.test.testcases import JwtAPITestCase, TagTestCaseMixin
from apps.misc.models import WikipediaTag
from services.wikipedia.interface import WikipediaService

faker = Faker()


class WikipediaServiceTestCase(JwtAPITestCase, TagTestCaseMixin):
    @patch("services.wikipedia.interface.WikipediaService.wbgetentities")
    def test_update_or_create_tag(self, mocked):
        wikipedia_qid = self.get_random_wikipedia_qid()
        mocked.return_value = self.get_wikipedia_tag_mocked_return(wikipedia_qid)
        WikipediaService.update_or_create_wikipedia_tag(wikipedia_qid)
        tag = WikipediaTag.objects.get(wikipedia_qid=wikipedia_qid)
        assert tag.name_fr == f"name_fr_{wikipedia_qid}"
        assert tag.name_en == tag.name == f"name_en_{wikipedia_qid}"
        assert tag.description_fr == f"description_fr_{wikipedia_qid}"
        assert (
            tag.description_en == tag.description == f"description_en_{wikipedia_qid}"
        )

    @patch("services.wikipedia.interface.WikipediaService.wbgetentities")
    def test_update_or_create_tag_no_english(self, mocked):
        wikipedia_qid = self.get_random_wikipedia_qid()
        mocked.return_value = self.get_wikipedia_tag_mocked_return(
            wikipedia_qid, en=False
        )
        WikipediaService.update_or_create_wikipedia_tag(wikipedia_qid)
        tag = WikipediaTag.objects.get(wikipedia_qid=wikipedia_qid)
        assert tag.name == tag.name_fr == tag.name_en == f"name_fr_{wikipedia_qid}"
        assert (
            tag.description
            == tag.description_fr
            == tag.description_en
            == f"description_fr_{wikipedia_qid}"
        )
