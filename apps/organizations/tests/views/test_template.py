import random

from django.urls import reverse
from faker import Faker
from parameterized import parameterized
from rest_framework import status

from apps.commons.test import JwtAPITestCase, TestRoles
from apps.organizations.factories import (
    OrganizationFactory,
    ProjectCategoryFactory,
    TemplateFactory,
)
from apps.organizations.models import Template
from apps.skills.factories import TagFactory

faker = Faker()


class CreateTemplateTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.tags = TagFactory.create_batch(3, organization=cls.organization)
        cls.categories = ProjectCategoryFactory.create_batch(
            3, organization=cls.organization
        )

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_201_CREATED),
            (TestRoles.ORG_ADMIN, status.HTTP_201_CREATED),
            (TestRoles.ORG_FACILITATOR, status.HTTP_403_FORBIDDEN),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_create_template(self, role, expected_code):
        user = self.get_parameterized_test_user(role, instances=[self.organization])
        self.client.force_authenticate(user)
        payload = {
            "name": faker.sentence(),
            "description": faker.text(),
            "project_title": faker.sentence(),
            "project_description": faker.text(),
            "blogentry_title": faker.sentence(),
            "blogentry_content": faker.text(),
            "goal_title": faker.sentence(),
            "goal_description": faker.text(),
            "review_title": faker.sentence(),
            "review_description": faker.text(),
            "audience": random.choice(Template.Audiences.values),  # nosec
            "time_estimation": random.choice(Template.TimeEstimation.values),  # nosec
            "share_globally": faker.boolean(),
            "categories_ids": [c.id for c in self.categories],
            "project_tags": [t.id for t in self.tags],
        }
        response = self.client.post(
            reverse("Template-list", args=(self.organization.code,)), data=payload
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_201_CREATED:
            content = response.json()
            self.assertEqual(content["organization"], self.organization.code)
            self.assertEqual(content["name"], payload["name"])
            self.assertEqual(content["description"], payload["description"])
            self.assertEqual(content["project_title"], payload["project_title"])
            self.assertEqual(
                content["project_description"], payload["project_description"]
            )
            self.assertEqual(content["blogentry_title"], payload["blogentry_title"])
            self.assertEqual(content["blogentry_content"], payload["blogentry_content"])
            self.assertEqual(content["goal_title"], payload["goal_title"])
            self.assertEqual(content["goal_description"], payload["goal_description"])
            self.assertEqual(content["review_title"], payload["review_title"])
            self.assertEqual(
                content["review_description"], payload["review_description"]
            )
            self.assertEqual(content["audience"], payload["audience"])
            self.assertEqual(content["time_estimation"], payload["time_estimation"])
            self.assertEqual(content["share_globally"], payload["share_globally"])
            self.assertSetEqual(
                {t["id"] for t in content["project_tags"]}, set(payload["project_tags"])
            )
            self.assertSetEqual(
                {t["id"] for t in content["categories"]}, set(payload["categories_ids"])
            )


class ReadTemplateTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.template = TemplateFactory(organization=cls.organization)
        TemplateFactory()

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS,),
            (TestRoles.DEFAULT,),
        ]
    )
    def test_list_template(self, role):
        user = self.get_parameterized_test_user(role, instances=[])
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("Template-list", args=(self.organization.code,))
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["id"], self.template.id)

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS,),
            (TestRoles.DEFAULT,),
        ]
    )
    def test_retrieve_template(self, role):
        user = self.get_parameterized_test_user(role, instances=[])
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("Template-detail", args=(self.organization.code, self.template.id))
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["id"], self.template.id)


class UpdateTemplateTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.template = TemplateFactory(organization=cls.organization)
        cls.tags = TagFactory.create_batch(3, organization=cls.organization)
        cls.categories = ProjectCategoryFactory.create_batch(
            3, organization=cls.organization
        )

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_ADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_FACILITATOR, status.HTTP_403_FORBIDDEN),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_update_template(self, role, expected_code):
        user = self.get_parameterized_test_user(role, instances=[self.organization])
        self.client.force_authenticate(user)
        payload = {
            "name": faker.sentence(),
            "description": faker.text(),
            "project_title": faker.sentence(),
            "project_description": faker.text(),
            "blogentry_title": faker.sentence(),
            "blogentry_content": faker.text(),
            "goal_title": faker.sentence(),
            "goal_description": faker.text(),
            "review_title": faker.sentence(),
            "review_description": faker.text(),
            "audience": random.choice(Template.Audiences.values),  # nosec
            "time_estimation": random.choice(Template.TimeEstimation.values),  # nosec
            "share_globally": faker.boolean(),
            "categories_ids": [c.id for c in self.categories],
            "project_tags": [t.id for t in self.tags],
        }
        response = self.client.patch(
            reverse("Template-detail", args=(self.organization.code, self.template.id)),
            data=payload,
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_200_OK:
            content = response.json()
            self.assertEqual(content["organization"], self.organization.code)
            self.assertEqual(content["name"], payload["name"])
            self.assertEqual(content["description"], payload["description"])
            self.assertEqual(content["project_title"], payload["project_title"])
            self.assertEqual(
                content["project_description"], payload["project_description"]
            )
            self.assertEqual(content["blogentry_title"], payload["blogentry_title"])
            self.assertEqual(content["blogentry_content"], payload["blogentry_content"])
            self.assertEqual(content["goal_title"], payload["goal_title"])
            self.assertEqual(content["goal_description"], payload["goal_description"])
            self.assertEqual(content["review_title"], payload["review_title"])
            self.assertEqual(
                content["review_description"], payload["review_description"]
            )
            self.assertEqual(content["audience"], payload["audience"])
            self.assertEqual(content["time_estimation"], payload["time_estimation"])
            self.assertEqual(content["share_globally"], payload["share_globally"])
            self.assertSetEqual(
                {t["id"] for t in content["project_tags"]}, set(payload["project_tags"])
            )
            self.assertSetEqual(
                {t["id"] for t in content["categories"]}, set(payload["categories_ids"])
            )


class DeleteTemplateTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_ADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_FACILITATOR, status.HTTP_403_FORBIDDEN),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_delete_template(self, role, expected_code):
        template = TemplateFactory(organization=self.organization)
        user = self.get_parameterized_test_user(role, instances=[self.organization])
        self.client.force_authenticate(user)
        response = self.client.delete(
            reverse("Template-detail", args=(self.organization.code, template.id))
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_204_NO_CONTENT:
            self.assertFalse(Template.objects.filter(id=template.id).exists())
