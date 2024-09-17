from unittest.mock import patch

from faker import Faker

from services.esco.factories import EscoOccupationFactory, EscoSkillFactory
from services.esco.models import EscoOccupation, EscoSkill, EscoUpdateError
from services.esco.testcases import EscoTestCase
from services.esco.utils import (
    create_missing_occupations,
    create_missing_skills,
    update_occupation_data,
    update_skill_data,
)

faker = Faker()


class EscoServiceTestCase(EscoTestCase):
    @patch("services.esco.interface.EscoService.get_all_objects")
    def test_create_missing_skills(self, mocked):
        existing_skill = EscoSkillFactory()
        uris = [existing_skill.uri, *[faker.uri() for _ in range(5)]]
        mocked.return_value = self.search_skills_return_value(uris)
        created_skills = create_missing_skills()
        self.assertEqual(len(created_skills), 5)
        skills = EscoSkill.objects.filter(uri__in=uris)
        self.assertEqual(len(skills), 6)

    @patch("services.esco.interface.EscoService.get_all_objects")
    def test_create_missing_occupations(self, mocked):
        existing_occupation = EscoOccupationFactory()
        uris = [existing_occupation.uri, *[faker.uri() for _ in range(5)]]
        mocked.return_value = self.search_occupations_return_value(uris)
        created_occupations = create_missing_occupations()
        self.assertEqual(len(created_occupations), 5)
        occupations = EscoOccupation.objects.filter(uri__in=uris)
        self.assertEqual(len(occupations), 6)

    @patch("services.esco.interface.EscoService.get_object_from_uri")
    def test_update_skill_data(self, mocked):
        skill = EscoSkillFactory()
        data = {
            "uri": skill.uri,
            "title_en": faker.sentence(),
            "title_fr": faker.sentence(),
            "description_en": faker.text(),
            "description_fr": faker.text(),
            "broader_skills": EscoSkillFactory.create_batch(2),
            "essential_for_skills": EscoSkillFactory.create_batch(2),
            "optional_for_skills": EscoSkillFactory.create_batch(2),
        }
        mocked.return_value = self.get_skill_return_value(**data)
        updated_skill = update_skill_data(skill)
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
            {skill.uri for skill in updated_skill.essential_for_skills.all()},
            {skill.uri for skill in data["essential_for_skills"]},
        )
        self.assertSetEqual(
            {skill.uri for skill in updated_skill.optional_for_skills.all()},
            {skill.uri for skill in data["optional_for_skills"]},
        )

    @patch("services.esco.interface.EscoService.get_object_from_uri")
    def test_update_occupation_data(self, mocked):
        occupation = EscoOccupationFactory()
        data = {
            "uri": occupation.uri,
            "title_en": faker.sentence(),
            "title_fr": faker.sentence(),
            "description_en": faker.text(),
            "description_fr": faker.text(),
            "broader_occupations": EscoOccupationFactory.create_batch(2),
            "essential_skills": EscoSkillFactory.create_batch(2),
            "optional_skills": EscoSkillFactory.create_batch(2),
        }
        mocked.return_value = self.get_occupation_return_value(**data)
        updated_occupation = update_occupation_data(occupation)
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
        skill = EscoSkillFactory()
        mocked.side_effect = self.raise_exception_side_effect
        update_skill_data(skill)
        error = EscoUpdateError.objects.filter(
            item_type="EscoSkill", item_id=int(skill.id), error="Exception"
        )
        self.assertTrue(error.exists())

    @patch("services.esco.utils._update_occupation_data")
    def test_update_occupation_data_error(self, mocked):
        occupation = EscoOccupationFactory()
        mocked.side_effect = self.raise_exception_side_effect
        update_occupation_data(occupation)
        error = EscoUpdateError.objects.filter(
            item_type="EscoOccupation", item_id=int(occupation.id), error="Exception"
        )
        self.assertTrue(error.exists())
