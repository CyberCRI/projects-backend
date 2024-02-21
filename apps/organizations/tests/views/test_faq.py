from django.urls import reverse
from faker import Faker
from parameterized import parameterized
from rest_framework import status

from apps.commons.test import JwtAPITestCase, TestRoles
from apps.organizations.factories import FaqFactory, OrganizationFactory
from apps.organizations.models import Faq

faker = Faker()


class CreateFaqTestCase(JwtAPITestCase):
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
    def test_create_faq(self, role, expected_code):
        user = self.get_parameterized_test_user(role, instances=[self.organization])
        self.client.force_authenticate(user)
        payload = {
            "title": faker.sentence(),
            "content": faker.text(),
            "organization_code": self.organization.code,
        }
        response = self.client.post(
            reverse("Faq-list", args=(self.organization.code,)),
            data=payload,
        )
        self.assertEqual(response.status_code, expected_code)
        if response.status_code == status.HTTP_201_CREATED:
            content = response.json()
            self.assertEqual(content["title"], payload["title"])
            self.assertEqual(content["content"], payload["content"])


class RetrieveFaqTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.faq = FaqFactory(organization=cls.organization)

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS,),
            (TestRoles.DEFAULT,),
        ]
    )
    def test_retrieve_faq(self, role):
        user = self.get_parameterized_test_user(role, instances=[self.organization])
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("Faq-list", args=(self.organization.code,)),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["title"], self.organization.faq.title)
        self.assertEqual(content["content"], self.organization.faq.content)


class UpdateFaqTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.faq = FaqFactory(organization=cls.organization)

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
    def test_update_faq(self, role, expected_code):
        user = self.get_parameterized_test_user(role, instances=[self.organization])
        self.client.force_authenticate(user)
        payload = {
            "title": faker.sentence(),
            "content": faker.text(),
        }
        response = self.client.patch(
            reverse("Faq-list", args=(self.organization.code,)),
            data=payload,
        )
        self.assertEqual(response.status_code, expected_code)
        if response.status_code == status.HTTP_200_OK:
            content = response.json()
            self.assertEqual(content["title"], payload["title"])
            self.assertEqual(content["content"], payload["content"])


class DeleteFaqTestCase(JwtAPITestCase):
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
    def test_delete_faq(self, role, expected_code):
        faq = FaqFactory(organization=self.organization)
        user = self.get_parameterized_test_user(role, instances=[self.organization])
        self.client.force_authenticate(user)
        response = self.client.delete(
            reverse("Faq-list", args=(self.organization.code,)),
        )
        self.assertEqual(response.status_code, expected_code)
        if response.status_code == status.HTTP_204_NO_CONTENT:
            self.assertFalse(Faq.objects.filter(id=faq.id).exists())
