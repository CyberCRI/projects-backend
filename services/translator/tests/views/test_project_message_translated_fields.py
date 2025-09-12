from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from faker import Faker
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory, ProjectMessageFactory
from apps.projects.models import ProjectMessage
from services.translator.models import AutoTranslatedField

faker = Faker()


class ProjectMessageTranslatedFieldsTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.project = ProjectFactory(organizations=[cls.organization])
        cls.superadmin = UserFactory(groups=[get_superadmins_group()])
        cls.content_type = ContentType.objects.get_for_model(ProjectMessage)

    def test_create_project_message(self):
        self.client.force_authenticate(self.superadmin)
        payload = {
            "content": faker.word(),
        }
        response = self.client.post(
            reverse("ProjectMessage-list", args=(self.project.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        content = response.json()
        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=content["id"]
        )
        self.assertEqual(
            auto_translated_fields.count(), len(ProjectMessage.auto_translated_fields)
        )
        self.assertSetEqual(
            {field.field_name for field in auto_translated_fields},
            set(ProjectMessage.auto_translated_fields),
        )
        for field in auto_translated_fields:
            self.assertFalse(field.up_to_date)

    def test_update_project_message(self):
        self.client.force_authenticate(self.superadmin)
        project_message = ProjectMessageFactory(project=self.project)
        AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=project_message.pk
        ).update(up_to_date=True)

        payload = {
            translated_field: faker.word()
            for translated_field in ProjectMessage.auto_translated_fields
        }
        response = self.client.patch(
            reverse(
                "ProjectMessage-detail", args=(self.project.id, project_message.pk)
            ),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=project_message.pk
        )
        self.assertEqual(
            auto_translated_fields.count(), len(ProjectMessage.auto_translated_fields)
        )
        self.assertSetEqual(
            {field.field_name for field in auto_translated_fields},
            set(ProjectMessage.auto_translated_fields),
        )
        for field in auto_translated_fields:
            if field.field_name in payload:
                self.assertFalse(field.up_to_date)
            else:
                self.assertTrue(field.up_to_date)

    def test_delete_project_message(self):
        self.client.force_authenticate(self.superadmin)
        project_message = ProjectMessageFactory(project=self.project)
        AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=project_message.pk
        ).update(up_to_date=True)

        response = self.client.delete(
            reverse("ProjectMessage-detail", args=(self.project.id, project_message.pk))
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=project_message.pk
        )
        self.assertEqual(auto_translated_fields.count(), 0)
