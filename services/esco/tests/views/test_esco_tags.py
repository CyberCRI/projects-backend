from django.urls import reverse
from rest_framework import status

from apps.commons.test import JwtAPITestCase
from services.esco.factories import EscoTagFactory
from services.esco.models import EscoTag


class EscoSkillViewsetTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.occupation_parents = EscoTagFactory.create_batch(
            2, type=EscoTag.EscoTagType.OCCUPATION
        )
        cls.occupation_essential_skills = EscoTagFactory.create_batch(
            2, type=EscoTag.EscoTagType.SKILL
        )
        cls.occupation_optional_skills = EscoTagFactory.create_batch(
            2, type=EscoTag.EscoTagType.SKILL
        )
        cls.occupation = EscoTagFactory(
            type=EscoTag.EscoTagType.OCCUPATION,
            parents=cls.occupation_parents,
            essential_skills=cls.occupation_essential_skills,
            optional_skills=cls.occupation_optional_skills,
        )
        cls.occupation_children = EscoTagFactory.create_batch(
            2, type=EscoTag.EscoTagType.OCCUPATION, parents=[cls.occupation]
        )

        cls.occupations = [
            cls.occupation,
            *cls.occupation_parents,
            *cls.occupation_children,
        ]

        cls.skill_parents = EscoTagFactory.create_batch(2)
        cls.skill_essential_skills = EscoTagFactory.create_batch(2)
        cls.skill_optional_skills = EscoTagFactory.create_batch(2)
        cls.skill = EscoTagFactory(
            parents=cls.skill_parents,
            essential_skills=cls.skill_essential_skills,
            optional_skills=cls.skill_optional_skills,
        )
        cls.skill_children = EscoTagFactory.create_batch(2, parents=[cls.skill])
        cls.skill_essential_for = EscoTagFactory.create_batch(
            2, essential_skills=[cls.skill]
        )
        cls.skill_optional_for = EscoTagFactory.create_batch(
            2, optional_skills=[cls.skill]
        )
        cls.skills = [
            cls.skill,
            *cls.skill_parents,
            *cls.skill_children,
            *cls.skill_essential_skills,
            *cls.skill_optional_skills,
            *cls.skill_essential_for,
            *cls.skill_optional_for,
            *cls.occupation_essential_skills,
            *cls.occupation_optional_skills,
        ]

        cls.tags = cls.occupations + cls.skills

    def test_list_esco_tags(self):
        response = self.client.get(reverse("EscoTag-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), len(self.tags))
        self.assertSetEqual(
            {tag["id"] for tag in content},
            {tag.id for tag in self.tags},
        )

    def test_retrieve_esco_occupation(self):
        response = self.client.get(
            reverse("EscoTag-detail", args=(self.occupation.id,))
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["id"], self.occupation.id)
        self.assertEqual(content["title_fr"], self.occupation.title_fr)
        self.assertEqual(content["title_en"], self.occupation.title_en)
        self.assertEqual(content["description_fr"], self.occupation.description_fr)
        self.assertEqual(content["description_en"], self.occupation.description_en)
        self.assertSetEqual(
            {parent["id"] for parent in content["parents"]},
            {parent.id for parent in self.occupation_parents},
        )
        self.assertSetEqual(
            {child["id"] for child in content["children"]},
            {child.id for child in self.occupation_children},
        )
        self.assertSetEqual(
            {skill["id"] for skill in content["essential_skills"]},
            {skill.id for skill in self.occupation_essential_skills},
        )
        self.assertSetEqual(
            {skill["id"] for skill in content["optional_skills"]},
            {skill.id for skill in self.occupation_optional_skills},
        )

    def test_retrieve_esco_skill(self):
        response = self.client.get(reverse("EscoTag-detail", args=(self.skill.id,)))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["id"], self.skill.id)
        self.assertEqual(content["title_fr"], self.skill.title_fr)
        self.assertEqual(content["title_en"], self.skill.title_en)
        self.assertEqual(content["description_fr"], self.skill.description_fr)
        self.assertEqual(content["description_en"], self.skill.description_en)
        self.assertSetEqual(
            {parent["id"] for parent in content["parents"]},
            {parent.id for parent in self.skill_parents},
        )
        self.assertSetEqual(
            {child["id"] for child in content["children"]},
            {child.id for child in self.skill_children},
        )
        self.assertSetEqual(
            {skill["id"] for skill in content["essential_skills"]},
            {skill.id for skill in self.skill_essential_skills},
        )
        self.assertSetEqual(
            {skill["id"] for skill in content["optional_skills"]},
            {skill.id for skill in self.skill_optional_skills},
        )

    def test_filter_by_type_occupation(self):
        response = self.client.get(
            reverse("EscoTag-list") + f"?type={EscoTag.EscoTagType.OCCUPATION}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), len(self.occupations))
        self.assertSetEqual(
            {tag["id"] for tag in content},
            {tag.id for tag in self.occupations},
        )

    def test_filter_by_type_skill(self):
        response = self.client.get(
            reverse("EscoTag-list") + f"?type={EscoTag.EscoTagType.SKILL}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), len(self.skills))
        self.assertSetEqual(
            {tag["id"] for tag in content},
            {tag.id for tag in self.skills},
        )

    def test_filter_occupation_by_parent(self):
        response = self.client.get(
            reverse("EscoTag-list") + f"?parents={self.occupation_parents[0].id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), 1)
        self.assertEqual(content[0]["id"], self.occupation.id)

    def test_filter_skill_by_parent(self):
        response = self.client.get(
            reverse("EscoTag-list") + f"?parents={self.skill_parents[0].id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), 1)
        self.assertEqual(content[0]["id"], self.skill.id)

    def test_filter_occuption_by_children(self):
        response = self.client.get(
            reverse("EscoTag-list") + f"?children={self.occupation_children[0].id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), 1)
        self.assertEqual(content[0]["id"], self.occupation.id)

    def test_filter_skill_by_children(self):
        response = self.client.get(
            reverse("EscoTag-list") + f"?children={self.skill_children[0].id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), 1)
        self.assertEqual(content[0]["id"], self.skill.id)

    def test_filter_occupation_by_essential_skill(self):
        response = self.client.get(
            reverse("EscoTag-list")
            + f"?essential_skills={self.occupation_essential_skills[0].id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), 1)
        self.assertEqual(content[0]["id"], self.occupation.id)

    def test_filter_skill_by_essential_skill(self):
        response = self.client.get(
            reverse("EscoTag-list")
            + f"?essential_skills={self.skill_essential_skills[0].id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), 1)
        self.assertEqual(content[0]["id"], self.skill.id)

    def test_filter_occupation_by_optional_skill(self):
        response = self.client.get(
            reverse("EscoTag-list")
            + f"?optional_skills={self.occupation_optional_skills[0].id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), 1)
        self.assertEqual(content[0]["id"], self.occupation.id)

    def test_filter_skill_by_optional_skill(self):
        response = self.client.get(
            reverse("EscoTag-list")
            + f"?optional_skills={self.skill_optional_skills[0].id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), 1)
        self.assertEqual(content[0]["id"], self.skill.id)

    def test_filter_skill_by_essential_for_skill(self):
        response = self.client.get(
            reverse("EscoTag-list") + f"?essential_for={self.skill_essential_for[0].id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), 1)
        self.assertEqual(content[0]["id"], self.skill.id)

    def test_filter_skill_by_optional_for_skill(self):
        response = self.client.get(
            reverse("EscoTag-list") + f"?optional_for={self.skill_optional_for[0].id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), 1)
        self.assertEqual(content[0]["id"], self.skill.id)
