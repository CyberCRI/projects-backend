from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from faker import Faker
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory, ProjectTabFactory
from apps.projects.models import ProjectTab
from services.translator.models import AutoTranslatedField

faker = Faker()


class ProjectTabTranslatedFieldsTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.project = ProjectFactory(organizations=[cls.organization])
        cls.superadmin = UserFactory(groups=[get_superadmins_group()])
        cls.content_type = ContentType.objects.get_for_model(ProjectTab)

    def test_create_project_tab(self):
        self.client.force_authenticate(self.superadmin)
        payload = {
            "type": ProjectTab.TabType.BLOG,
            "icon": faker.word(),
            "title": faker.word(),
            "description": faker.word(),
        }
        response = self.client.post(
            reverse("ProjectTab-list", args=(self.project.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        content = response.json()
        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=content["id"]
        )
        self.assertEqual(
            auto_translated_fields.count(), len(ProjectTab._auto_translated_fields)
        )
        self.assertSetEqual(
            {field.field_name for field in auto_translated_fields},
            set(ProjectTab._auto_translated_fields),
        )
        for field in auto_translated_fields:
            self.assertFalse(field.up_to_date)

    def test_update_project_tab(self):
        self.client.force_authenticate(self.superadmin)
        project_tab = ProjectTabFactory(project=self.project)
        AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=project_tab.pk
        ).update(up_to_date=True)

        # Update one translated field
        payload = {
            ProjectTab._auto_translated_fields[0]: faker.word(),
        }
        response = self.client.patch(
            reverse("ProjectTab-detail", args=(self.project.id, project_tab.pk)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=project_tab.pk
        )
        self.assertEqual(
            auto_translated_fields.count(), len(ProjectTab._auto_translated_fields)
        )
        for field in auto_translated_fields:
            if field.field_name in payload:
                self.assertFalse(field.up_to_date)
            else:
                self.assertTrue(field.up_to_date)

        # Update all translated fields
        payload = {
            translated_field: faker.word()
            for translated_field in ProjectTab._auto_translated_fields
        }
        response = self.client.patch(
            reverse("ProjectTab-detail", args=(self.project.id, project_tab.pk)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=project_tab.pk
        )
        self.assertEqual(
            auto_translated_fields.count(), len(ProjectTab._auto_translated_fields)
        )
        self.assertSetEqual(
            {field.field_name for field in auto_translated_fields},
            set(ProjectTab._auto_translated_fields),
        )
        for field in auto_translated_fields:
            if field.field_name in payload:
                self.assertFalse(field.up_to_date)
            else:
                self.assertTrue(field.up_to_date)

    def test_delete_project_tab(self):
        self.client.force_authenticate(self.superadmin)
        project_tab = ProjectTabFactory(project=self.project)
        AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=project_tab.pk
        ).update(up_to_date=True)

        response = self.client.delete(
            reverse("ProjectTab-detail", args=(self.project.id, project_tab.pk))
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=project_tab.pk
        )
        self.assertEqual(auto_translated_fields.count(), 0)
