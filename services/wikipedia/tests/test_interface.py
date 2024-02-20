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
        self.assertEqual(tag.name_fr, f"name_fr_{wikipedia_qid}")
        self.assertEqual(tag.name_en, tag.name == f"name_en_{wikipedia_qid}")
        self.assertEqual(tag.description_fr, f"description_fr_{wikipedia_qid}")
        self.assertEqual(tag.description_en, f"description_en_{wikipedia_qid}")
        self.assertEqual(tag.description, tag.description_en)

    @patch("services.wikipedia.interface.WikipediaService.wbgetentities")
    def test_update_or_create_tag_no_english(self, mocked):
        wikipedia_qid = self.get_random_wikipedia_qid()
        mocked.return_value = self.get_wikipedia_tag_mocked_return(
            wikipedia_qid, en=False
        )
        WikipediaService.update_or_create_wikipedia_tag(wikipedia_qid)
        tag = WikipediaTag.objects.get(wikipedia_qid=wikipedia_qid)
        self.assertEqual(tag.name_fr, f"name_fr_{wikipedia_qid}")
        self.assertEqual(tag.name_en, tag.name_fr)
        self.assertEqual(tag.name, tag.name_fr)
        self.assertEqual(tag.description_fr, f"description_fr_{wikipedia_qid}")
        self.assertEqual(tag.description_en, tag.description_fr)
        self.assertEqual(tag.description, tag.description_fr)
