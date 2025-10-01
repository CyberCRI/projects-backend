from django.urls import reverse
from faker import Faker
from parameterized import parameterized
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase, TestRoles
from apps.organizations.factories import OrganizationFactory, ProjectCategoryFactory
from apps.organizations.models import ProjectCategory
from apps.projects.factories import ProjectFactory
from apps.projects.models import Project
from apps.skills.factories import TagFactory

faker = Faker()


class CreateProjectCategoryTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.tags = TagFactory.create_batch(3, organization=cls.organization)

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
    def test_create_project_category(self, role, expected_code):
        user = self.get_parameterized_test_user(role, instances=[self.organization])
        self.client.force_authenticate(user)
        payload = {
            "organization_code": self.organization.code,
            "name": faker.sentence(),
            "description": faker.text(),
            "tags": [t.id for t in self.tags],
            "order_index": faker.pyint(0, 10),
            "background_color": faker.color(),
            "foreground_color": faker.color(),
            "is_reviewable": faker.boolean(),
        }
        response = self.client.post(reverse("Category-list"), data=payload)
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_201_CREATED:
            content = response.json()
            self.assertEqual(content["organization"], self.organization.code)
            self.assertEqual(content["name"], payload["name"])
            self.assertEqual(content["description"], payload["description"])
            self.assertSetEqual(
                {t["id"] for t in content["tags"]}, set(payload["tags"])
            )
            self.assertEqual(content["order_index"], payload["order_index"])
            self.assertEqual(content["background_color"], payload["background_color"])
            self.assertEqual(content["foreground_color"], payload["foreground_color"])
            self.assertEqual(content["is_reviewable"], payload["is_reviewable"])


class ReadProjectCategoryTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.category = ProjectCategoryFactory(organization=cls.organization)
        cls.projects = ProjectFactory.create_batch(
            3, organizations=[cls.organization], categories=[cls.category]
        )

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
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["id"], self.category.id)
        self.assertEqual(content["results"][0]["projects_count"], 3)

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
        self.assertEqual(content["id"], self.category.id)
        self.assertEqual(content["projects_count"], 3)


class UpdateProjectCategoryTestCase(JwtAPITestCase):
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
    def test_update_project_category(self, role, expected_code):
        tags = TagFactory.create_batch(3, organization=self.organization)
        user = self.get_parameterized_test_user(role, instances=[self.organization])
        self.client.force_authenticate(user)
        payload = {
            "name": faker.sentence(),
            "description": faker.text(),
            "tags": [t.id for t in tags],
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
            self.assertEqual(content["name"], payload["name"])
            self.assertEqual(content["description"], payload["description"])
            self.assertSetEqual(
                {t["id"] for t in content["tags"]}, {t.id for t in tags}
            )
            self.assertEqual(content["order_index"], payload["order_index"])
            self.assertEqual(content["background_color"], payload["background_color"])
            self.assertEqual(content["foreground_color"], payload["foreground_color"])
            self.assertEqual(content["is_reviewable"], payload["is_reviewable"])


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
            self.assertFalse(ProjectCategory.objects.filter(id=category.id).exists())


class ProjectCategoryProjectStatusTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.category = ProjectCategoryFactory(organization=cls.organization)
        cls.other_project = ProjectFactory(
            life_status=Project.LifeStatus.RUNNING,
            is_locked=False,
        )

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_ADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_FACILITATOR, status.HTTP_200_OK),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_update_project_life_status(self, role, expected_code):
        user = self.get_parameterized_test_user(role, instances=[self.organization])
        self.client.force_authenticate(user)
        projects = ProjectFactory.create_batch(
            2,
            life_status=Project.LifeStatus.RUNNING,
            is_locked=False,
            organizations=[self.organization],
            categories=[self.category],
        )
        payload = {
            "life_status": Project.LifeStatus.COMPLETED,
        }
        response = self.client.post(
            reverse("Category-projects-life-status", args=(self.category.id,)),
            data=payload,
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_200_OK:
            for project in projects:
                project.refresh_from_db()
                self.assertEqual(project.life_status, Project.LifeStatus.COMPLETED)
            self.assertEqual(self.other_project.life_status, Project.LifeStatus.RUNNING)

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_ADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_FACILITATOR, status.HTTP_200_OK),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_update_project_locked_status(self, role, expected_code):
        user = self.get_parameterized_test_user(role, instances=[self.organization])
        self.client.force_authenticate(user)
        projects = ProjectFactory.create_batch(
            2,
            life_status=Project.LifeStatus.RUNNING,
            is_locked=False,
            organizations=[self.organization],
            categories=[self.category],
        )
        payload = {
            "is_locked": True,
        }
        response = self.client.post(
            reverse("Category-projects-locked-status", args=(self.category.id,)),
            data=payload,
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_200_OK:
            for project in projects:
                project.refresh_from_db()
                self.assertEqual(project.is_locked, True)
            self.assertEqual(self.other_project.is_locked, False)


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
                "comment": faker.text(),
            },
        }
        response = self.client.post(reverse("Category-list"), data=payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        content = response.json()
        template = content["template"]
        payload_template = payload["template"]
        self.assertEqual(
            template["title_placeholder"], payload_template["title_placeholder"]
        )
        self.assertEqual(
            template["description_placeholder"],
            payload_template["description_placeholder"],
        )
        self.assertEqual(
            template["goal_placeholder"], payload_template["goal_placeholder"]
        )
        self.assertEqual(
            template["blogentry_title_placeholder"],
            payload_template["blogentry_title_placeholder"],
        )
        self.assertEqual(
            template["blogentry_placeholder"], payload_template["blogentry_placeholder"]
        )
        self.assertEqual(template["goal_title"], payload_template["goal_title"])
        self.assertEqual(
            template["goal_description"], payload_template["goal_description"]
        )
        self.assertEqual(template["comment"], payload_template["comment"])

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
                "comment": faker.text(),
            },
        }
        response = self.client.patch(
            reverse("Category-detail", args=(category.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        template = content["template"]
        payload_template = payload["template"]
        self.assertEqual(
            template["title_placeholder"], payload_template["title_placeholder"]
        )
        self.assertEqual(
            template["description_placeholder"],
            payload_template["description_placeholder"],
        )
        self.assertEqual(
            template["goal_placeholder"], payload_template["goal_placeholder"]
        )
        self.assertEqual(
            template["blogentry_title_placeholder"],
            payload_template["blogentry_title_placeholder"],
        )
        self.assertEqual(
            template["blogentry_placeholder"], payload_template["blogentry_placeholder"]
        )
        self.assertEqual(template["goal_title"], payload_template["goal_title"])
        self.assertEqual(
            template["goal_description"], payload_template["goal_description"]
        )
        self.assertEqual(template["comment"], payload_template["comment"])

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
        self.assertEqual(
            template["title_placeholder"], payload["template"]["title_placeholder"]
        )
        self.assertEqual(
            template["description_placeholder"],
            original_template.description_placeholder,
        )
        self.assertEqual(
            template["goal_placeholder"], original_template.goal_placeholder
        )
        self.assertEqual(
            template["blogentry_title_placeholder"],
            original_template.blogentry_title_placeholder,
        )
        self.assertEqual(
            template["blogentry_placeholder"], original_template.blogentry_placeholder
        )
        self.assertEqual(template["goal_title"], original_template.goal_title)
        self.assertEqual(
            template["goal_description"], original_template.goal_description
        )


class ValidateProjectCategoryTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.user = UserFactory(groups=[get_superadmins_group()])

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=self.user)

    def test_create_parent_in_other_organization(self):
        parent = ProjectCategoryFactory()
        payload = {
            "organization_code": self.organization.code,
            "name": faker.sentence(),
            "description": faker.text(),
            "parent": parent.id,
        }
        response = self.client.post(reverse("Category-list"), data=payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertApiValidationError(
            response,
            {"parent": ["The parent category must belong to the same organization"]},
        )

    def test_update_parent_in_other_organization(self):
        category = ProjectCategoryFactory(organization=self.organization)
        parent = ProjectCategoryFactory()
        payload = {
            "parent": parent.id,
        }
        response = self.client.patch(
            reverse("Category-detail", args=(category.id,)), payload
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertApiValidationError(
            response,
            {"parent": ["The parent category must belong to the same organization"]},
        )

    def test_own_parent(self):
        category = ProjectCategoryFactory(organization=self.organization)
        payload = {
            "parent": category.id,
        }
        response = self.client.patch(
            reverse("Category-detail", args=(category.id,)), payload
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertApiValidationError(
            response,
            {"parent": ["You are trying to create a loop in the category's hierarchy"]},
        )

    def test_create_hierarchy_loop(self):
        category_1 = ProjectCategoryFactory(organization=self.organization)
        category_2 = ProjectCategoryFactory(
            organization=self.organization, parent=category_1
        )
        category_3 = ProjectCategoryFactory(
            organization=self.organization, parent=category_2
        )
        payload = {"parent": category_3.id}
        response = self.client.patch(
            reverse("Category-detail", args=(category_1.id,)), payload
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertApiValidationError(
            response,
            {"parent": ["You are trying to create a loop in the category's hierarchy"]},
        )

    def test_set_root_category_as_parent_with_none(self):
        child = ProjectCategoryFactory(organization=self.organization)
        payload = {"parent": None}
        response = self.client.patch(
            reverse("Category-detail", args=(child.id,)), payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        child.refresh_from_db()
        self.assertEqual(
            child.parent,
            ProjectCategory.update_or_create_root(self.organization),
        )


class MiscProjectCategoryTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.superadmin = UserFactory(groups=[get_superadmins_group()])

    def test_get_slug(self):
        name = "My AMazing pROjecT categORy !"
        category = ProjectCategoryFactory(name=name, organization=self.organization)
        self.assertEqual(category.slug, "my-amazing-project-category")
        category = ProjectCategoryFactory(name=name, organization=self.organization)
        self.assertEqual(category.slug, "my-amazing-project-category-1")
        category = ProjectCategoryFactory(name=name, organization=self.organization)
        self.assertEqual(category.slug, "my-amazing-project-category-2")
        category = ProjectCategoryFactory(name="123", organization=self.organization)
        self.assertTrue(category.slug.startswith("category-"))

    def test_outdated_slug(self):
        self.client.force_authenticate(self.superadmin)
        name_a = "name-a"
        name_b = "name-b"
        name_c = "name-c"
        category = ProjectCategoryFactory(name=name_a, organization=self.organization)

        # Check that the slug is updated and the old one is stored in outdated_slugs
        payload = {"name": name_b}
        response = self.client.patch(
            reverse("Category-detail", args=(category.id,)), payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        category.refresh_from_db()
        self.assertEqual(category.slug, "name-b")
        self.assertSetEqual({"name-a"}, set(category.outdated_slugs))

        # Check that multiple_slug is correctly updated
        payload = {"name": name_c}
        response = self.client.patch(
            reverse("Category-detail", args=(category.id,)),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        category.refresh_from_db()
        self.assertEqual(category.slug, "name-c")
        self.assertSetEqual({"name-a", "name-b"}, set(category.outdated_slugs))

        # Check that outdated_slugs are reused if relevant
        payload = {"name": name_b}
        response = self.client.patch(
            reverse("Category-detail", args=(category.id,)),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        category.refresh_from_db()
        self.assertEqual(category.slug, "name-b")
        self.assertSetEqual(
            {"name-a", "name-b", "name-c"}, set(category.outdated_slugs)
        )

        # Check that outdated_slugs respect unicity
        payload = {
            "name": name_a,
            "organization_code": self.organization.code,
        }
        response = self.client.post(reverse("Category-list"), data=payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        content = response.json()
        self.assertEqual(content["slug"], "name-a-1")
