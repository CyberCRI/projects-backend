from django.urls import reverse
from rest_framework import status

from apps.commons.test import JwtAPITestCase
from services.esco.factories import EscoOccupationFactory, EscoSkillFactory


class EscoSkillViewsetTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.parents = EscoOccupationFactory.create_batch(2)
        cls.essential_skills = EscoSkillFactory.create_batch(2)
        cls.optional_skills = EscoSkillFactory.create_batch(2)
        cls.occupation = EscoOccupationFactory(
            parents=cls.parents,
            essential_skills=cls.essential_skills,
            optional_skills=cls.optional_skills,
        )
        cls.children = EscoOccupationFactory.create_batch(2, parents=[cls.occupation])
        cls.occupations = [
            cls.occupation,
            *cls.parents,
            *cls.children,
        ]

    def test_list_esco_occupations(self):
        response = self.client.get(reverse("EscoOccupation-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), len(self.occupations))
        self.assertSetEqual(
            {occupation["id"] for occupation in content},
            {occupation.id for occupation in self.occupations},
        )

    def test_retrieve_esco_occupation(self):
        response = self.client.get(
            reverse("EscoOccupation-detail", args=(self.occupation.id,))
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
            reverse("EscoOccupation-list") + f"?parents={self.parents[0].id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), 1)
        self.assertEqual(content[0]["id"], self.occupation.id)

    def test_filter_by_children(self):
        response = self.client.get(
            reverse("EscoOccupation-list") + f"?children={self.children[0].id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), 1)
        self.assertEqual(content[0]["id"], self.occupation.id)

    def test_filter_by_essential_skill(self):
        response = self.client.get(
            reverse("EscoOccupation-list")
            + f"?essential_skills={self.essential_skills[0].id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), 1)
        self.assertEqual(content[0]["id"], self.occupation.id)

    def test_filter_by_optional_skill(self):
        response = self.client.get(
            reverse("EscoOccupation-list")
            + f"?optional_skills={self.optional_skills[0].id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), 1)
        self.assertEqual(content[0]["id"], self.occupation.id)
