from unittest.mock import patch

from django.urls import reverse
from faker import Faker
from parameterized import parameterized
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase, TestRoles
from apps.commons.test.testcases import TagTestCaseMixin
from apps.organizations.factories import OrganizationFactory, ProjectCategoryFactory
from apps.organizations.models import ProjectCategory

faker = Faker()


class CreateProjectCategoryTestCase(JwtAPITestCase, TagTestCaseMixin):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()

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
    @patch("services.wikipedia.interface.WikipediaService.wbgetentities")
    def test_create_project_category(self, role, expected_code, mocked):
        mocked.side_effect = self.get_wikipedia_tag_mocked_side_effect
        wikipedia_qids = [self.get_random_wikipedia_qid() for _ in range(3)]
        user = self.get_parameterized_test_user(role, instances=[self.organization])
        self.client.force_authenticate(user)
        payload = {
            "organization_code": self.organization.code,
            "name": faker.sentence(),
            "description": faker.text(),
            "wikipedia_tags_ids": wikipedia_qids,
            "order_index": faker.pyint(0, 10),
            "background_color": faker.color(),
            "foreground_color": faker.color(),
            "is_reviewable": faker.boolean(),
        }
        response = self.client.post(reverse("Category-list"), data=payload)
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_201_CREATED:
            content = response.json()
            assert content["organization"] == self.organization.code
            assert content["name"] == payload["name"]
            assert content["description"] == payload["description"]
            assert {t["wikipedia_qid"] for t in content["wikipedia_tags"]} == set(
                wikipedia_qids
            )
            assert content["order_index"] == payload["order_index"]
            assert content["background_color"] == payload["background_color"]
            assert content["foreground_color"] == payload["foreground_color"]
            assert content["is_reviewable"] == payload["is_reviewable"]


class ReadProjectCategoryTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.category = ProjectCategoryFactory(organization=cls.organization)

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS,),
            (TestRoles.DEFAULT,),
        ]
    )
    def test_list_project_category(self, role):
        user = self.get_parameterized_test_user(role, instances=[])
        self.client.force_authenticate(user)
        response = self.client.get(reverse("Category-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        assert content["count"] == 1
        assert content["results"][0]["id"] == self.category.id

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS,),
            (TestRoles.DEFAULT,),
        ]
    )
    def test_retrieve_project_category(self, role):
        user = self.get_parameterized_test_user(role, instances=[])
        self.client.force_authenticate(user)
        response = self.client.get(reverse("Category-detail", args=(self.category.id,)))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        assert content["id"] == self.category.id


class UpdateProjectCategoryTestCase(JwtAPITestCase, TagTestCaseMixin):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.category = ProjectCategoryFactory(organization=cls.organization)

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
    @patch("services.wikipedia.interface.WikipediaService.wbgetentities")
    def test_update_project_category(self, role, expected_code, mocked):
        mocked.side_effect = self.get_wikipedia_tag_mocked_side_effect
        wikipedia_qids = [self.get_random_wikipedia_qid() for _ in range(3)]
        user = self.get_parameterized_test_user(role, instances=[self.organization])
        self.client.force_authenticate(user)
        payload = {
            "name": faker.sentence(),
            "description": faker.text(),
            "wikipedia_tags_ids": wikipedia_qids,
            "order_index": faker.pyint(0, 10),
            "background_color": faker.color(),
            "foreground_color": faker.color(),
            "is_reviewable": faker.boolean(),
        }
        response = self.client.patch(
            reverse("Category-detail", args=(self.category.id,)), data=payload
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_201_CREATED:
            content = response.json()
            assert content["name"] == payload["name"]
            assert content["description"] == payload["description"]
            assert {t["wikipedia_qid"] for t in content["wikipedia_tags"]} == set(
                wikipedia_qids
            )
            assert content["order_index"] == payload["order_index"]
            assert content["background_color"] == payload["background_color"]
            assert content["foreground_color"] == payload["foreground_color"]
            assert content["is_reviewable"] == payload["is_reviewable"]


class DeleteProjectCategoryTestCase(JwtAPITestCase):
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
    def test_delete_project_category(self, role, expected_code):
        category = ProjectCategoryFactory(organization=self.organization)
        user = self.get_parameterized_test_user(role, instances=[self.organization])
        self.client.force_authenticate(user)
        response = self.client.delete(reverse("Category-detail", args=(category.id,)))
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_204_NO_CONTENT:
            assert not ProjectCategory.objects.filter(id=category.id).exists()


class ProjectCategoryTemplateTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.superadmin = UserFactory(groups=[get_superadmins_group()])

    def test_create_with_template(self):
        self.client.force_authenticate(self.superadmin)
        payload = {
            "organization_code": self.organization.code,
            "name": faker.sentence(),
            "description": faker.text(),
            "order_index": faker.pyint(0, 10),
            "background_color": faker.color(),
            "foreground_color": faker.color(),
            "is_reviewable": faker.boolean(),
            "template": {
                "title_placeholder": faker.sentence(),
                "description_placeholder": faker.text(),
                "goal_placeholder": faker.sentence(),
                "blogentry_title_placeholder": faker.sentence(),
                "blogentry_placeholder": faker.text(),
                "goal_title": faker.sentence(),
                "goal_description": faker.text(),
            },
        }
        response = self.client.post(reverse("Category-list"), data=payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        content = response.json()
        template = content["template"]
        payload_template = payload["template"]
        assert template["title_placeholder"] == payload_template["title_placeholder"]
        assert (
            template["description_placeholder"]
            == payload_template["description_placeholder"]
        )
        assert template["goal_placeholder"] == payload_template["goal_placeholder"]
        assert (
            template["blogentry_title_placeholder"]
            == payload_template["blogentry_title_placeholder"]
        )
        assert (
            template["blogentry_placeholder"]
            == payload_template["blogentry_placeholder"]
        )
        assert template["goal_title"] == payload_template["goal_title"]
        assert template["goal_description"] == payload_template["goal_description"]

    def test_update_template(self):
        self.client.force_authenticate(self.superadmin)
        category = ProjectCategoryFactory(organization=self.organization)
        payload = {
            "template": {
                "title_placeholder": faker.sentence(),
                "description_placeholder": faker.text(),
                "goal_placeholder": faker.sentence(),
                "blogentry_title_placeholder": faker.sentence(),
                "blogentry_placeholder": faker.text(),
                "goal_title": faker.sentence(),
                "goal_description": faker.text(),
            },
        }
        response = self.client.patch(
            reverse("Category-detail", args=(category.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        template = content["template"]
        payload_template = payload["template"]
        assert template["title_placeholder"] == payload_template["title_placeholder"]
        assert (
            template["description_placeholder"]
            == payload_template["description_placeholder"]
        )
        assert template["goal_placeholder"] == payload_template["goal_placeholder"]
        assert (
            template["blogentry_title_placeholder"]
            == payload_template["blogentry_title_placeholder"]
        )
        assert (
            template["blogentry_placeholder"]
            == payload_template["blogentry_placeholder"]
        )
        assert template["goal_title"] == payload_template["goal_title"]
        assert template["goal_description"] == payload_template["goal_description"]

    def test_partial_update_template(self):
        self.client.force_authenticate(self.superadmin)
        category = ProjectCategoryFactory(organization=self.organization)
        original_template = category.template
        payload = {
            "template": {
                "title_placeholder": faker.sentence(),
            },
        }
        response = self.client.patch(
            reverse("Category-detail", args=(category.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        template = content["template"]
        assert template["title_placeholder"] == payload["template"]["title_placeholder"]
        assert (
            template["description_placeholder"]
            == original_template.description_placeholder
        )
        assert template["goal_placeholder"] == original_template.goal_placeholder
        assert (
            template["blogentry_title_placeholder"]
            == original_template.blogentry_title_placeholder
        )
        assert (
            template["blogentry_placeholder"] == original_template.blogentry_placeholder
        )
        assert template["goal_title"] == original_template.goal_title
        assert template["goal_description"] == original_template.goal_description
