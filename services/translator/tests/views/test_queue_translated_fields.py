from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from faker import Faker
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory
from apps.projects.models import Project
from services.translator.models import AutoTranslatedField

faker = Faker()


class CreateProjectTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.superadmin = UserFactory(groups=[get_superadmins_group()])
        cls.content_type = ContentType.objects.get_for_model(Project)

    def test_create_project(self):
        self.client.force_authenticate(self.superadmin)
        payload = {
            "organizations_codes": [self.organization.code],
            "title": faker.sentence(),
        }
        response = self.client.post(reverse("Project-list"), data=payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        content = response.json()
        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=content["id"]
        )
        self.assertEqual(auto_translated_fields.count(), 2)
        self.assertSetEqual(
            {field.field_name for field in auto_translated_fields},
            {"title", "description"},
        )
        for field in auto_translated_fields:
            self.assertFalse(field.up_to_date)

    def test_create_project_with_description(self):
        self.client.force_authenticate(self.superadmin)
        payload = {
            "organizations_codes": [self.organization.code],
            "title": faker.sentence(),
            "description": faker.sentence(),
        }
        response = self.client.post(reverse("Project-list"), data=payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        content = response.json()
        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=content["id"]
        )
        self.assertEqual(auto_translated_fields.count(), 2)
        self.assertSetEqual(
            {field.field_name for field in auto_translated_fields},
            {"title", "description"},
        )
        for field in auto_translated_fields:
            self.assertFalse(field.up_to_date)

    def test_update_project(self):
        self.client.force_authenticate(self.superadmin)
        project = ProjectFactory(organizations=[self.organization])
        AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=project.pk
        ).update(up_to_date=True)

        response = self.client.patch(
            reverse("Project-detail", args=(project.pk,)),
            data={"sdgs": [1]},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=project.pk
        )
        self.assertEqual(auto_translated_fields.count(), 2)
        self.assertSetEqual(
            {field.field_name for field in auto_translated_fields},
            {"title", "description"},
        )
        for field in auto_translated_fields:
            self.assertTrue(field.up_to_date)

    def test_update_project_one_translated_field(self):
        self.client.force_authenticate(self.superadmin)
        project = ProjectFactory(organizations=[self.organization])
        AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=project.pk
        ).update(up_to_date=True)

        response = self.client.patch(
            reverse("Project-detail", args=(project.pk,)),
            data={"title": faker.sentence()},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=project.pk
        )
        self.assertEqual(auto_translated_fields.count(), 2)
        self.assertSetEqual(
            {field.field_name for field in auto_translated_fields},
            {"title", "description"},
        )
        for field in auto_translated_fields:
            if field.field_name == "title":
                self.assertFalse(field.up_to_date)
            else:
                self.assertTrue(field.up_to_date)

    def test_update_project_multiple_translated_fields(self):
        self.client.force_authenticate(self.superadmin)
        project = ProjectFactory(organizations=[self.organization])
        AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=project.pk
        ).update(up_to_date=True)

        payload = {
            "title": faker.sentence(),
            "description": faker.sentence(),
        }
        response = self.client.patch(
            reverse("Project-detail", args=(project.pk,)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=project.pk
        )
        self.assertEqual(auto_translated_fields.count(), 2)
        self.assertSetEqual(
            {field.field_name for field in auto_translated_fields},
            {"title", "description"},
        )
        for field in auto_translated_fields:
            self.assertFalse(field.up_to_date)

    def test_delete_project(self):
        self.client.force_authenticate(self.superadmin)
        project = ProjectFactory(organizations=[self.organization])
        AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=project.pk
        ).update(up_to_date=True)

        response = self.client.delete(reverse("Project-detail", args=(project.pk,)))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=project.pk
        )
        self.assertEqual(auto_translated_fields.count(), 0)
