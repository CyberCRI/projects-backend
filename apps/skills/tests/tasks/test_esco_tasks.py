from unittest.mock import patch

from faker import Faker

from apps.skills.factories import TagFactory
from apps.skills.models import Tag
from apps.skills.testcases import EscoTestCase
from apps.skills.utils import create_missing_tags, update_tag_data

faker = Faker()


class EscoServiceTestCase(EscoTestCase):
    @patch("services.esco.interface.EscoService.get_all_objects")
    def test_create_missing_tags(self, mocked):
        existing_skill = TagFactory(
            type=Tag.TagType.ESCO, secondary_type=Tag.SecondaryTagType.SKILL
        )
        existing_occupation = TagFactory(
            type=Tag.TagType.ESCO, secondary_type=Tag.SecondaryTagType.OCCUPATION
        )
        skills_uris = [
            existing_skill.external_id,
            *[f"{faker.uri()}{i}/{i}" for i in range(5)],
        ]
        occupations_uris = [
            existing_occupation.external_id,
            *[f"{faker.uri()}{i}/{i}" for i in range(5)],
        ]
        mocked.side_effect = [
            self.search_skills_return_value(skills_uris),
            self.search_occupations_return_value(occupations_uris),
        ]
        created_tags = create_missing_tags()
        self.assertEqual(len(created_tags), 10)
        skills = Tag.objects.filter(
            external_id__in=skills_uris,
            type=Tag.TagType.ESCO,
            secondary_type=Tag.SecondaryTagType.SKILL,
        )
        self.assertEqual(skills.count(), 6)
        occupations = Tag.objects.filter(
            external_id__in=occupations_uris,
            type=Tag.TagType.ESCO,
            secondary_type=Tag.SecondaryTagType.OCCUPATION,
        )
        self.assertEqual(occupations.count(), 6)

    @patch("services.esco.interface.EscoService.get_object_from_uri")
    def test_update_skill_data(self, mocked):
        skill = TagFactory(
            type=Tag.TagType.ESCO, secondary_type=Tag.SecondaryTagType.SKILL
        )
        data = {
            "uri": skill.external_id,
            "title_en": faker.sentence(),
            "title_fr": faker.sentence(),
            "description_en": faker.text(),
            "description_fr": faker.text(),
        }
        mocked.return_value = self.get_skill_return_value(**data)
        updated_skill = update_tag_data(skill)
        self.assertEqual(updated_skill.title, data["title_en"])
        self.assertEqual(updated_skill.title_en, data["title_en"])
        self.assertEqual(updated_skill.title_fr, data["title_fr"])
        self.assertEqual(updated_skill.description, data["description_en"])
        self.assertEqual(updated_skill.description_en, data["description_en"])
        self.assertEqual(updated_skill.description_fr, data["description_fr"])

    @patch("services.esco.interface.EscoService.get_object_from_uri")
    def test_update_occupation_data(self, mocked):
        occupation = TagFactory(
            type=Tag.TagType.ESCO, secondary_type=Tag.SecondaryTagType.OCCUPATION
        )
        data = {
            "uri": occupation.external_id,
            "title_en": faker.sentence(),
            "title_fr": faker.sentence(),
            "description_en": faker.text(),
            "description_fr": faker.text(),
        }
        mocked.return_value = self.get_occupation_return_value(**data)
        updated_occupation = update_tag_data(occupation)
        self.assertEqual(updated_occupation.title, data["title_en"])
        self.assertEqual(updated_occupation.title_en, data["title_en"])
        self.assertEqual(updated_occupation.title_fr, data["title_fr"])
        self.assertEqual(updated_occupation.description, data["description_en"])
        self.assertEqual(updated_occupation.description_en, data["description_en"])
        self.assertEqual(updated_occupation.description_fr, data["description_fr"])
