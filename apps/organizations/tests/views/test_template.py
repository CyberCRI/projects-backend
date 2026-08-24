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
from apps.organizations.models import Template, TemplateTab
from apps.projects.models import ProjectTab
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
            "project_purpose": faker.text(),
            "blogentry_title": faker.sentence(),
            "blogentry_content": faker.text(),
            "goal_title": faker.sentence(),
            "goal_description": faker.text(),
            "review_title": faker.sentence(),
            "review_description": faker.text(),
            "comment_content": faker.text(),
            "categories_ids": [c.id for c in self.categories],
            "project_tags": [t.id for t in self.tags],
            "enable_tab": False,
            "tabs": [],
        }
        response = self.client.post(
            reverse("Template-list", args=(self.organization.code,)),
            data=payload,
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
            self.assertEqual(content["project_purpose"], payload["project_purpose"])
            self.assertEqual(content["blogentry_title"], payload["blogentry_title"])
            self.assertEqual(content["blogentry_content"], payload["blogentry_content"])
            self.assertEqual(content["goal_title"], payload["goal_title"])
            self.assertEqual(content["goal_description"], payload["goal_description"])
            self.assertEqual(content["review_title"], payload["review_title"])
            self.assertEqual(content["enable_tab"], payload["enable_tab"])
            self.assertEqual(content["tabs"], payload["tabs"])
            self.assertEqual(
                content["review_description"], payload["review_description"]
            )
            self.assertEqual(content["comment_content"], payload["comment_content"])
            self.assertSetEqual(
                {t["id"] for t in content["project_tags"]},
                set(payload["project_tags"]),
            )
            self.assertSetEqual(
                {t["id"] for t in content["categories"]},
                set(payload["categories_ids"]),
            )

    def test_create_template_tabs(self):
        user = self.get_parameterized_test_user(
            TestRoles.ORG_ADMIN, instances=[self.organization]
        )
        self.client.force_authenticate(user)

        def create_template(tabs):
            payload = {
                "name": faker.sentence(),
                "description": faker.text(),
                "project_title": faker.sentence(),
                "project_description": faker.text(),
                "project_purpose": faker.text(),
                "blogentry_title": faker.sentence(),
                "blogentry_content": faker.text(),
                "goal_title": faker.sentence(),
                "goal_description": faker.text(),
                "review_title": faker.sentence(),
                "review_description": faker.text(),
                "comment_content": faker.text(),
                "categories_ids": [c.id for c in self.categories],
                "project_tags": [t.id for t in self.tags],
                "enable_tab": False,
                "tabs": tabs,
            }
            return self.client.post(
                reverse("Template-list", args=(self.organization.code,)),
                data=payload,
            )

        # no template
        template = create_template([]).json()
        self.assertEqual(template["tabs"], [])

        tab = {
            "title": faker.text(),
            "description": faker.text(),
            "type": ProjectTab.TabType.TEXT,
            "icon": faker.text(),
            "show_preview": False,
            "title_item": faker.text(),
            "content_item": faker.text(),
        }
        template = create_template([tab]).json()
        self.assertEqual(len(template["tabs"]), 1)
        # check tabs is equal
        for key, value in tab.items():
            self.assertEqual(value, template["tabs"][0][key])
        # uuid/id is created
        self.assertIsNotNone(template["tabs"][0]["uuid"])
        self.assertIsNotNone(template["tabs"][0]["id"])

        # error invalid template
        response = create_template([{}])
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # invalid type
        response = create_template([{**tab, "type": "invalid type"}])
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ReadTemplateTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.template = TemplateFactory(organization=cls.organization)
        TemplateFactory()

    @parameterized.expand([(TestRoles.ANONYMOUS,), (TestRoles.DEFAULT,)])
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

    @parameterized.expand([(TestRoles.ANONYMOUS,), (TestRoles.DEFAULT,)])
    def test_retrieve_template(self, role):
        user = self.get_parameterized_test_user(role, instances=[])
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse(
                "Template-detail",
                args=(self.organization.code, self.template.id),
            )
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
            "project_purpose": faker.text(),
            "blogentry_title": faker.sentence(),
            "blogentry_content": faker.text(),
            "goal_title": faker.sentence(),
            "goal_description": faker.text(),
            "review_title": faker.sentence(),
            "review_description": faker.text(),
            "comment_content": faker.text(),
            "categories_ids": [c.id for c in self.categories],
            "project_tags": [t.id for t in self.tags],
        }
        response = self.client.patch(
            reverse(
                "Template-detail",
                args=(self.organization.code, self.template.id),
            ),
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
            self.assertEqual(content["project_purpose"], payload["project_purpose"])
            self.assertEqual(content["blogentry_title"], payload["blogentry_title"])
            self.assertEqual(content["blogentry_content"], payload["blogentry_content"])
            self.assertEqual(content["goal_title"], payload["goal_title"])
            self.assertEqual(content["goal_description"], payload["goal_description"])
            self.assertEqual(content["review_title"], payload["review_title"])
            self.assertEqual(
                content["review_description"], payload["review_description"]
            )
            self.assertEqual(content["comment_content"], payload["comment_content"])
            self.assertSetEqual(
                {t["id"] for t in content["project_tags"]},
                set(payload["project_tags"]),
            )
            self.assertSetEqual(
                {t["id"] for t in content["categories"]},
                set(payload["categories_ids"]),
            )

    def test_update_template_tabs(self):
        user = self.get_parameterized_test_user(
            TestRoles.ORG_ADMIN, instances=[self.organization]
        )
        self.client.force_authenticate(user)

        def update_template(payload):
            return self.client.patch(
                reverse(
                    "Template-detail",
                    args=(self.organization.code, self.template.id),
                ),
                data=payload,
            )

        # no template
        template = update_template({"tabs": []}).json()
        self.assertEqual(template["tabs"], [])

        tab = {
            "title": faker.text(),
            "description": faker.text(),
            "type": ProjectTab.TabType.TEXT,
            "icon": faker.text(),
            "show_preview": False,
            "title_item": faker.text(),
            "content_item": faker.text(),
        }
        template = update_template({"tabs": [tab]}).json()
        self.assertEqual(len(template["tabs"]), 1)
        # check tabs is equal
        for key, value in tab.items():
            self.assertEqual(value, template["tabs"][0][key])
        # uuid/id is created
        self.assertIsNotNone(template["tabs"][0]["uuid"])
        self.assertIsNotNone(template["tabs"][0]["id"])

        # update template
        tab = template["tabs"][0]
        tab["title"] = faker.text()
        tab["show_preview"] = False

        template = update_template({"tabs": [tab]}).json()
        self.assertEqual(template["tabs"][0]["title"], tab["title"])
        self.assertEqual(template["tabs"][0]["show_preview"], tab["show_preview"])

        # delete template
        tab_id = tab["id"]
        template = update_template({"tabs": []}).json()
        self.assertEqual(template["tabs"], [])
        self.assertFalse(TemplateTab.objects.filter(id=tab_id).exists())

        # error invalid template
        response = update_template([{}])
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # invalid type
        response = update_template([{**tab, "type": "invalid type"}])
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


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
