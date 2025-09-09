from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from faker import Faker
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase
from apps.feedbacks.factories import ReviewFactory
from apps.feedbacks.models import Review
from apps.organizations.factories import OrganizationFactory, ProjectCategoryFactory
from apps.projects.factories import ProjectFactory
from apps.projects.models import Project
from services.translator.models import AutoTranslatedField

faker = Faker()


class ReviewTranslatedFieldsTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.category = ProjectCategoryFactory(
            organization=cls.organization, is_reviewable=True
        )
        cls.project = ProjectFactory(
            organizations=[cls.organization],
            life_status=Project.LifeStatus.TO_REVIEW,
            categories=[cls.category],
        )
        cls.superadmin = UserFactory(groups=[get_superadmins_group()])
        cls.content_type = ContentType.objects.get_for_model(Review)

    def test_create_review(self):
        self.client.force_authenticate(self.superadmin)
        payload = {
            "title": faker.text(),
            "description": faker.text(),
            "project_id": self.project.id,
        }
        response = self.client.post(
            reverse("Reviewed-list", args=(self.project.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        content = response.json()
        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=content["id"]
        )
        self.assertEqual(
            auto_translated_fields.count(), len(Review.auto_translated_fields)
        )
        self.assertSetEqual(
            {field.field_name for field in auto_translated_fields},
            set(Review.auto_translated_fields),
        )
        for field in auto_translated_fields:
            self.assertFalse(field.up_to_date)

    def test_update_review(self):
        self.client.force_authenticate(self.superadmin)
        review = ReviewFactory(project=self.project)
        AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=review.pk
        ).update(up_to_date=True)

        payload = {
            translated_field: faker.word()
            for translated_field in Review.auto_translated_fields
        }
        response = self.client.patch(
            reverse("Reviewed-detail", args=(self.project.id, review.pk)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=review.pk
        )
        self.assertEqual(
            auto_translated_fields.count(), len(Review.auto_translated_fields)
        )
        self.assertSetEqual(
            {field.field_name for field in auto_translated_fields},
            set(Review.auto_translated_fields),
        )
        for field in auto_translated_fields:
            if field.field_name in payload:
                self.assertFalse(field.up_to_date)
            else:
                self.assertTrue(field.up_to_date)

    def test_delete_review(self):
        self.client.force_authenticate(self.superadmin)
        review = ReviewFactory(project=self.project)
        AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=review.pk
        ).update(up_to_date=True)

        response = self.client.delete(
            reverse("Reviewed-detail", args=(self.project.id, review.pk))
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=review.pk
        )
        self.assertEqual(auto_translated_fields.count(), 0)
