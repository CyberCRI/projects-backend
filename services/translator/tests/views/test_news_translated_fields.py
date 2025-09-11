import datetime

from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from faker import Faker
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase
from apps.newsfeed.factories import NewsFactory
from apps.newsfeed.models import News
from apps.organizations.factories import OrganizationFactory
from services.translator.models import AutoTranslatedField

faker = Faker()


class NewsTranslatedFieldsTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.superadmin = UserFactory(groups=[get_superadmins_group()])
        cls.content_type = ContentType.objects.get_for_model(News)

    def test_create_news(self):
        self.client.force_authenticate(self.superadmin)
        payload = {
            "organization": self.organization.code,
            "title": faker.word(),
            "content": faker.word(),
            "publication_date": datetime.date.today().isoformat(),
        }
        response = self.client.post(
            reverse("News-list", args=(self.organization.code,)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        content = response.json()
        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=content["id"]
        )
        self.assertEqual(
            auto_translated_fields.count(), len(News.auto_translated_fields)
        )
        self.assertSetEqual(
            {field.field_name for field in auto_translated_fields},
            set(News.auto_translated_fields),
        )
        for field in auto_translated_fields:
            self.assertFalse(field.up_to_date)

    def test_update_news(self):
        self.client.force_authenticate(self.superadmin)
        news = NewsFactory(organization=self.organization)
        AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=news.pk
        ).update(up_to_date=True)

        # Update one translated field
        payload = {
            News.auto_translated_fields[0]: faker.word(),
        }
        response = self.client.patch(
            reverse("News-detail", args=(self.organization.code, news.pk)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=news.pk
        )
        self.assertEqual(
            auto_translated_fields.count(), len(News.auto_translated_fields)
        )
        for field in auto_translated_fields:
            if field.field_name in payload:
                self.assertFalse(field.up_to_date)
            else:
                self.assertTrue(field.up_to_date)

        # Update all translated fields
        payload = {
            translated_field: faker.word()
            for translated_field in News.auto_translated_fields
        }
        response = self.client.patch(
            reverse("News-detail", args=(self.organization.code, news.pk)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=news.pk
        )
        self.assertEqual(
            auto_translated_fields.count(), len(News.auto_translated_fields)
        )
        self.assertSetEqual(
            {field.field_name for field in auto_translated_fields},
            set(News.auto_translated_fields),
        )
        for field in auto_translated_fields:
            if field.field_name in payload:
                self.assertFalse(field.up_to_date)
            else:
                self.assertTrue(field.up_to_date)

    def test_delete_news(self):
        self.client.force_authenticate(self.superadmin)
        news = NewsFactory(organization=self.organization)
        AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=news.pk
        ).update(up_to_date=True)

        response = self.client.delete(
            reverse("News-detail", args=(self.organization.code, news.pk))
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        auto_translated_fields = AutoTranslatedField.objects.filter(
            content_type=self.content_type, object_id=news.pk
        )
        self.assertEqual(auto_translated_fields.count(), 0)
