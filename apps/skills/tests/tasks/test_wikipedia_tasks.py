from unittest.mock import patch

from faker import Faker

from apps.skills.models import Tag, TagClassification
from apps.skills.testcases import WikipediaTestCase
from apps.skills.utils import update_or_create_wikipedia_tags

faker = Faker()


class WikipediaServiceTestCase(WikipediaTestCase):
    @patch("services.wikipedia.interface.WikipediaService.wbgetentities")
    def test_update_or_create_tag(self, mocked):
        wikipedia_qids = [self.get_random_wikipedia_qid() for _ in range(3)]
        mocked.return_value = self.get_wikipedia_tags_mocked_return(wikipedia_qids)
        update_or_create_wikipedia_tags(wikipedia_qids)
        classification = TagClassification.get_or_create_default_classification(
            classification_type=TagClassification.TagClassificationType.WIKIPEDIA
        )
        classification_tags = classification.tags.all()
        for wikipedia_qid in wikipedia_qids:
            tag = Tag.objects.get(external_id=wikipedia_qid)
            self.assertEqual(tag.title_fr, f"title_fr_{wikipedia_qid}")
            self.assertEqual(tag.title_en, f"title_en_{wikipedia_qid}")
            self.assertEqual(tag.title, tag.title_en)
            self.assertEqual(tag.description_fr, f"description_fr_{wikipedia_qid}")
            self.assertEqual(tag.description_en, f"description_en_{wikipedia_qid}")
            self.assertEqual(tag.description, tag.description_en)
            self.assertIn(tag, classification_tags)

    @patch("services.wikipedia.interface.WikipediaService.wbgetentities")
    def test_update_or_create_tag_no_english(self, mocked):
        wikipedia_qids = [self.get_random_wikipedia_qid() for _ in range(3)]
        mocked.return_value = self.get_wikipedia_tags_mocked_return(
            wikipedia_qids, en=False
        )
        update_or_create_wikipedia_tags(wikipedia_qids)
        classification = TagClassification.get_or_create_default_classification(
            classification_type=TagClassification.TagClassificationType.WIKIPEDIA
        )
        classification_tags = classification.tags.all()
        for wikipedia_qid in wikipedia_qids:
            tag = Tag.objects.get(external_id=wikipedia_qid)
            self.assertEqual(tag.title_fr, f"title_fr_{wikipedia_qid}")
            self.assertEqual(tag.title_en, tag.title_fr)
            self.assertEqual(tag.title, tag.title_fr)
            self.assertEqual(tag.description_fr, f"description_fr_{wikipedia_qid}")
            self.assertEqual(tag.description_en, tag.description_fr)
            self.assertEqual(tag.description, tag.description_fr)
            self.assertIn(tag, classification_tags)
