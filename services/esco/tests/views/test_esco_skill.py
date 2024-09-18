from django.urls import reverse
from rest_framework import status

from apps.commons.test import JwtAPITestCase
from services.esco.factories import EscoOccupationFactory, EscoSkillFactory


class EscoSkillViewsetTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.parents = EscoSkillFactory.create_batch(2)
        cls.essential_skills = EscoSkillFactory.create_batch(2)
        cls.optional_skills = EscoSkillFactory.create_batch(2)
        cls.skill = EscoSkillFactory(
            parents=cls.parents,
            essential_skills=cls.essential_skills,
            optional_skills=cls.optional_skills,
        )
        cls.children = EscoSkillFactory.create_batch(2, parents=[cls.skill])
        cls.essential_for_skills = EscoSkillFactory.create_batch(
            2, essential_skills=[cls.skill]
        )
        cls.optional_for_skills = EscoSkillFactory.create_batch(
            2, optional_skills=[cls.skill]
        )
        cls.skills = [
            cls.skill,
            *cls.parents,
            *cls.children,
            *cls.essential_skills,
            *cls.optional_skills,
            *cls.essential_for_skills,
            *cls.optional_for_skills,
        ]
        cls.optional_for_occupations = EscoOccupationFactory.create_batch(
            2, optional_skills=[cls.skill]
        )
        cls.essential_for_occupations = EscoOccupationFactory.create_batch(
            2, essential_skills=[cls.skill]
        )

    def test_list_esco_skills(self):
        response = self.client.get(reverse("EscoSkill-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), len(self.skills))
        self.assertSetEqual(
            {skill["id"] for skill in content}, {skill.id for skill in self.skills}
        )

    def test_retrieve_esco_skill(self):
        response = self.client.get(reverse("EscoSkill-detail", args=(self.skill.id,)))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["id"], self.skill.id)
        self.assertEqual(content["title_fr"], self.skill.title_fr)
        self.assertEqual(content["title_en"], self.skill.title_en)
        self.assertEqual(content["description_fr"], self.skill.description_fr)
        self.assertEqual(content["description_en"], self.skill.description_en)
        self.assertSetEqual(
            {parent["id"] for parent in content["parents"]},
            {parent.id for parent in self.parents},
        )
        self.assertSetEqual(
            {child["id"] for child in content["children"]},
            {child.id for child in self.children},
        )
        self.assertSetEqual(
            {skill["id"] for skill in content["essential_skills"]},
            {skill.id for skill in self.essential_skills},
        )
        self.assertSetEqual(
            {skill["id"] for skill in content["optional_skills"]},
            {skill.id for skill in self.optional_skills},
        )

    def test_filter_by_parent(self):
        response = self.client.get(
            reverse("EscoSkill-list") + f"?parents={self.parents[0].id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), 1)
        self.assertEqual(content[0]["id"], self.skill.id)

    def test_filter_by_children(self):
        response = self.client.get(
            reverse("EscoSkill-list") + f"?children={self.children[0].id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), 1)
        self.assertEqual(content[0]["id"], self.skill.id)

    def test_filter_by_essential_skill(self):
        response = self.client.get(
            reverse("EscoSkill-list")
            + f"?essential_skills={self.essential_skills[0].id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), 1)
        self.assertEqual(content[0]["id"], self.skill.id)

    def test_filter_by_essential_for_skill(self):
        response = self.client.get(
            reverse("EscoSkill-list")
            + f"?essential_for_skills={self.essential_for_skills[0].id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), 1)
        self.assertEqual(content[0]["id"], self.skill.id)

    def test_filter_by_optional_skill(self):
        response = self.client.get(
            reverse("EscoSkill-list") + f"?optional_skills={self.optional_skills[0].id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), 1)
        self.assertEqual(content[0]["id"], self.skill.id)

    def test_filter_by_optional_for_skill(self):
        response = self.client.get(
            reverse("EscoSkill-list")
            + f"?optional_for_skills={self.optional_for_skills[0].id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), 1)
        self.assertEqual(content[0]["id"], self.skill.id)

    def test_filter_by_essential_for_occupation(self):
        response = self.client.get(
            reverse("EscoSkill-list")
            + f"?essential_for_occupations={self.essential_for_occupations[0].id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), 1)
        self.assertEqual(content[0]["id"], self.skill.id)

    def test_filter_by_optional_for_occupation(self):
        response = self.client.get(
            reverse("EscoSkill-list")
            + f"?optional_for_occupations={self.optional_for_occupations[0].id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), 1)
        self.assertEqual(content[0]["id"], self.skill.id)
