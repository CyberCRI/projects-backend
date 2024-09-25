from unittest.mock import patch

from faker import Faker

from services.esco.factories import EscoTagFactory
from services.esco.models import EscoTag, EscoUpdateError
from services.esco.testcases import EscoTestCase
from services.esco.utils import create_missing_tags, update_tag_data

faker = Faker()


class EscoServiceTestCase(EscoTestCase):
    @patch("services.esco.interface.EscoService.get_all_objects")
    def test_create_missing_tags(self, mocked):
        existing_skill = EscoTagFactory(type=EscoTag.EscoTagType.SKILL)
        existing_occupation = EscoTagFactory(type=EscoTag.EscoTagType.OCCUPATION)
        skills_uris = [existing_skill.uri, *[f"{faker.uri()}{i}/{i}" for i in range(5)]]
        occupations_uris = [
            existing_occupation.uri,
            *[f"{faker.uri()}{i}/{i}" for i in range(5)],
        ]
        mocked.side_effect = [
            self.search_skills_return_value(skills_uris),
            self.search_occupations_return_value(occupations_uris),
        ]
        created_tags = create_missing_tags()
        self.assertEqual(len(created_tags), 10)
        skills = EscoTag.objects.filter(
            uri__in=skills_uris, type=EscoTag.EscoTagType.SKILL
        )
        self.assertEqual(skills.count(), 6)
        occupations = EscoTag.objects.filter(
            uri__in=occupations_uris, type=EscoTag.EscoTagType.OCCUPATION
        )
        self.assertEqual(occupations.count(), 6)

    @patch("services.esco.interface.EscoService.get_object_from_uri")
    def test_update_skill_data(self, mocked):
        skill = EscoTagFactory(type=EscoTag.EscoTagType.SKILL)
        data = {
            "uri": skill.uri,
            "title_en": faker.sentence(),
            "title_fr": faker.sentence(),
            "description_en": faker.text(),
            "description_fr": faker.text(),
            "broader_skills": EscoTagFactory.create_batch(
                2, type=EscoTag.EscoTagType.SKILL
            ),
            "essential_for_skills": EscoTagFactory.create_batch(
                2, type=EscoTag.EscoTagType.SKILL
            ),
            "optional_for_skills": EscoTagFactory.create_batch(
                2, type=EscoTag.EscoTagType.SKILL
            ),
        }
        mocked.return_value = self.get_skill_return_value(**data)
        updated_skill = update_tag_data(skill)
        self.assertEqual(updated_skill.title, data["title_en"])
        self.assertEqual(updated_skill.title_en, data["title_en"])
        self.assertEqual(updated_skill.title_fr, data["title_fr"])
        self.assertEqual(updated_skill.description, data["description_en"])
        self.assertEqual(updated_skill.description_en, data["description_en"])
        self.assertEqual(updated_skill.description_fr, data["description_fr"])
        self.assertSetEqual(
            {skill.uri for skill in updated_skill.parents.all()},
            {skill.uri for skill in data["broader_skills"]},
        )
        self.assertSetEqual(
            {skill.uri for skill in updated_skill.essential_for.all()},
            {skill.uri for skill in data["essential_for_skills"]},
        )
        self.assertSetEqual(
            {skill.uri for skill in updated_skill.optional_for.all()},
            {skill.uri for skill in data["optional_for_skills"]},
        )

    @patch("services.esco.interface.EscoService.get_object_from_uri")
    def test_update_occupation_data(self, mocked):
        occupation = EscoTagFactory(type=EscoTag.EscoTagType.OCCUPATION)
        data = {
            "uri": occupation.uri,
            "title_en": faker.sentence(),
            "title_fr": faker.sentence(),
            "description_en": faker.text(),
            "description_fr": faker.text(),
            "broader_occupations": EscoTagFactory.create_batch(
                2, type=EscoTag.EscoTagType.OCCUPATION
            ),
            "essential_skills": EscoTagFactory.create_batch(
                2, type=EscoTag.EscoTagType.SKILL
            ),
            "optional_skills": EscoTagFactory.create_batch(
                2, type=EscoTag.EscoTagType.SKILL
            ),
        }
        mocked.return_value = self.get_occupation_return_value(**data)
        updated_occupation = update_tag_data(occupation)
        self.assertEqual(updated_occupation.title, data["title_en"])
        self.assertEqual(updated_occupation.title_en, data["title_en"])
        self.assertEqual(updated_occupation.title_fr, data["title_fr"])
        self.assertEqual(updated_occupation.description, data["description_en"])
        self.assertEqual(updated_occupation.description_en, data["description_en"])
        self.assertEqual(updated_occupation.description_fr, data["description_fr"])
        self.assertSetEqual(
            {occupation.uri for occupation in updated_occupation.parents.all()},
            {occupation.uri for occupation in data["broader_occupations"]},
        )
        self.assertSetEqual(
            {skill.uri for skill in updated_occupation.essential_skills.all()},
            {skill.uri for skill in data["essential_skills"]},
        )
        self.assertSetEqual(
            {skill.uri for skill in updated_occupation.optional_skills.all()},
            {skill.uri for skill in data["optional_skills"]},
        )

    @patch("services.esco.utils._update_skill_data")
    def test_update_skill_data_error(self, mocked):
        skill = EscoTagFactory(type=EscoTag.EscoTagType.SKILL)
        mocked.side_effect = self.raise_exception_side_effect
        update_tag_data(skill)
        error = EscoUpdateError.objects.filter(
            item_type=EscoTag.EscoTagType.SKILL,
            item_id=int(skill.id),
            error="Exception",
        )
        self.assertTrue(error.exists())

    @patch("services.esco.utils._update_occupation_data")
    def test_update_occupation_data_error(self, mocked):
        occupation = EscoTagFactory(type=EscoTag.EscoTagType.OCCUPATION)
        mocked.side_effect = self.raise_exception_side_effect
        update_tag_data(occupation)
        error = EscoUpdateError.objects.filter(
            item_type=EscoTag.EscoTagType.OCCUPATION,
            item_id=int(occupation.id),
            error="Exception",
        )
        self.assertTrue(error.exists())
