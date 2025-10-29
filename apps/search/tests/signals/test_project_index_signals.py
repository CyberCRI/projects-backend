from unittest.mock import call, patch

from django.db.models.query import QuerySet
from django.test import override_settings
from django.urls import reverse
from faker import Faker
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase
from apps.organizations.factories import OrganizationFactory, ProjectCategoryFactory
from apps.projects.factories import ProjectFactory
from apps.projects.models import Project
from apps.skills.factories import TagFactory

faker = Faker()


class ProjectIndexUpdateSignalTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.category = ProjectCategoryFactory(organization=cls.organization)
        cls.category_to_add = ProjectCategoryFactory(organization=cls.organization)
        cls.tag = TagFactory(organization=cls.organization)
        cls.tag_to_add = TagFactory(organization=cls.organization)
        cls.project = ProjectFactory(
            organizations=[cls.organization], categories=[cls.category]
        )
        cls.project.tags.add(cls.tag)
        cls.main_owner = UserFactory(groups=[cls.project.get_owners()])
        cls.member_to_add = UserFactory()
        cls.member_to_remove = UserFactory(groups=[cls.project.get_members()])
        cls.superadmin = UserFactory(groups=[get_superadmins_group()])

    @staticmethod
    def mocked_update(*args, **kwargs):
        pass

    @patch("django_opensearch_dsl.documents.Document.update")
    @override_settings(OPENSEARCH_DSL_AUTO_REFRESH=True, OPENSEARCH_DSL_AUTOSYNC=True)
    def test_signal_called_on_project_create(self, mocked_update):
        mocked_update.side_effect = self.mocked_update

        self.client.force_authenticate(self.superadmin)
        payload = {
            "title": faker.sentence(),
            "description": faker.text(),
            "is_locked": faker.boolean(),
            "is_shareable": faker.boolean(),
            "purpose": faker.sentence(),
            "organizations_codes": [self.organization.code],
            "images_ids": [],
        }
        response = self.client.post(reverse("Project-list"), data=payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        mocked_update.assert_has_calls(
            [call(Project.objects.get(id=response.json()["id"]), "index")]
        )

    @patch("django_opensearch_dsl.documents.Document.update")
    @override_settings(OPENSEARCH_DSL_AUTO_REFRESH=True, OPENSEARCH_DSL_AUTOSYNC=True)
    def test_signal_called_on_project_update(self, mocked_update):
        mocked_update.side_effect = self.mocked_update

        self.client.force_authenticate(self.superadmin)
        payload = {"title": faker.sentence()}
        response = self.client.patch(
            reverse("Project-detail", args=(self.project.id,)), payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mocked_update.assert_has_calls([call(self.project, "index")])

    @patch("django_opensearch_dsl.documents.Document.update")
    @override_settings(OPENSEARCH_DSL_AUTO_REFRESH=True, OPENSEARCH_DSL_AUTOSYNC=True)
    def test_signal_called_on_add_members(self, mocked_update):
        mocked_update.side_effect = self.mocked_update

        self.client.force_authenticate(self.superadmin)
        payload = {"members": [self.member_to_add.id]}
        response = self.client.post(
            reverse("Project-add-member", args=(self.project.id,)), payload
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        mocked_update.assert_has_calls([call(self.project, "index")])

    @patch("django_opensearch_dsl.documents.Document.update")
    @override_settings(OPENSEARCH_DSL_AUTO_REFRESH=True, OPENSEARCH_DSL_AUTOSYNC=True)
    def test_signal_called_on_remove_members(self, mocked_update):
        mocked_update.side_effect = self.mocked_update

        self.client.force_authenticate(self.superadmin)
        payload = {"users": [self.member_to_remove.id]}
        response = self.client.post(
            reverse("Project-remove-member", args=(self.project.id,)), payload
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        mocked_update.assert_has_calls([call(self.project, "index")])

    @patch("django_opensearch_dsl.documents.Document.update")
    @override_settings(OPENSEARCH_DSL_AUTO_REFRESH=True, OPENSEARCH_DSL_AUTOSYNC=True)
    def test_signal_called_on_add_category(self, mocked_update):
        mocked_update.side_effect = self.mocked_update

        self.client.force_authenticate(self.superadmin)
        payload = {
            "project_categories_ids": [self.category_to_add.id, self.category.id]
        }
        response = self.client.patch(
            reverse("Project-detail", args=(self.project.id,)), payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mocked_update.assert_has_calls([call(self.project, "index")])

    @patch("django_opensearch_dsl.documents.Document.update")
    @override_settings(OPENSEARCH_DSL_AUTO_REFRESH=True, OPENSEARCH_DSL_AUTOSYNC=True)
    def test_signal_called_on_change_category(self, mocked_update):
        mocked_update.side_effect = self.mocked_update

        self.client.force_authenticate(self.superadmin)
        payload = {"name": faker.word()}
        response = self.client.patch(
            reverse(
                "Category-detail",
                args=(
                    self.organization.code,
                    self.category.id,
                ),
            ),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            any(
                self.project in call_args[0][0] and call_args[0][1] == "index"
                for call_args in mocked_update.call_args_list
                if len(call_args[0]) == 2
                and isinstance((call_args[0][0]), QuerySet)
                and call_args[0][0].model == Project
            )
        )

    @patch("django_opensearch_dsl.documents.Document.update")
    @override_settings(OPENSEARCH_DSL_AUTO_REFRESH=True, OPENSEARCH_DSL_AUTOSYNC=True)
    def test_signal_called_on_add_tags(self, mocked_update):
        mocked_update.side_effect = self.mocked_update

        self.client.force_authenticate(self.superadmin)
        payload = {"tags": [self.tag_to_add.id, self.tag.id]}
        response = self.client.patch(
            reverse("Project-detail", args=(self.project.id,)), payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mocked_update.assert_has_calls([call(self.project, "index")])

    @patch("django_opensearch_dsl.documents.Document.update")
    @override_settings(OPENSEARCH_DSL_AUTO_REFRESH=True, OPENSEARCH_DSL_AUTOSYNC=True)
    def test_signal_called_on_change_tags(self, mocked_update):
        mocked_update.side_effect = self.mocked_update

        self.client.force_authenticate(self.superadmin)
        title = faker.word()
        payload = {"title": title, "title_en": title, "title_fr": title}
        response = self.client.patch(
            reverse(
                "OrganizationTag-detail", args=(self.organization.code, self.tag.id)
            ),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            any(
                self.project in call_args[0][0] and call_args[0][1] == "index"
                for call_args in mocked_update.call_args_list
                if len(call_args[0]) == 2
                and isinstance((call_args[0][0]), QuerySet)
                and call_args[0][0].model == Project
            )
        )
