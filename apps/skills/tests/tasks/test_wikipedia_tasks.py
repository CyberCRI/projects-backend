from unittest.mock import patch

from faker import Faker

from apps.commons.test import JwtAPITestCase, TagTestCaseMixin
from apps.skills.models import Tag
from apps.skills.utils import update_or_create_wikipedia_tag

faker = Faker()


class WikipediaServiceTestCase(JwtAPITestCase, TagTestCaseMixin):
    @patch("services.wikipedia.interface.WikipediaService.wbgetentities")
    def test_update_or_create_tag(self, mocked):
        wikipedia_qid = self.get_random_wikipedia_qid()
        mocked.return_value = self.get_wikipedia_tag_mocked_return(wikipedia_qid)
        update_or_create_wikipedia_tag(wikipedia_qid)
        tag = Tag.objects.get(external_id=wikipedia_qid)
        self.assertEqual(tag.title_fr, f"title_fr_{wikipedia_qid}")
        self.assertEqual(tag.title_en, f"title_en_{wikipedia_qid}")
        self.assertEqual(tag.title, tag.title_en)
        self.assertEqual(tag.description_fr, f"description_fr_{wikipedia_qid}")
        self.assertEqual(tag.description_en, f"description_en_{wikipedia_qid}")
        self.assertEqual(tag.description, tag.description_en)

    @patch("services.wikipedia.interface.WikipediaService.wbgetentities")
    def test_update_or_create_tag_no_english(self, mocked):
        wikipedia_qid = self.get_random_wikipedia_qid()
        mocked.return_value = self.get_wikipedia_tag_mocked_return(
            wikipedia_qid, en=False
        )
        update_or_create_wikipedia_tag(wikipedia_qid)
        tag = Tag.objects.get(external_id=wikipedia_qid)
        self.assertEqual(tag.title_fr, f"title_fr_{wikipedia_qid}")
        self.assertEqual(tag.title_en, tag.title_fr)
        self.assertEqual(tag.title, tag.title_fr)
        self.assertEqual(tag.description_fr, f"description_fr_{wikipedia_qid}")
        self.assertEqual(tag.description_en, tag.description_fr)
        self.assertEqual(tag.description, tag.description_fr)
