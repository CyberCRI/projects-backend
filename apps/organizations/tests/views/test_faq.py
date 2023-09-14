from django.urls import reverse
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase
from apps.organizations import factories, models


class FaqTestCaseNoPermission(JwtAPITestCase):
    def test_create_no_permission(self):
        fake = factories.FaqFactory.build()
        organization = factories.OrganizationFactory()
        self.client.force_authenticate(UserFactory())
        payload = {
            "title": fake.title,
            "content": fake.content,
            "organization_code": organization.code,
        }
        response = self.client.post(
            reverse("Faq-list", kwargs={"organization_code": organization.code}),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_retrieve_no_permission(self):
        organization = factories.OrganizationFactory()
        organization_two = factories.OrganizationFactory()
        self.client.force_authenticate(UserFactory())
        response = self.client.get(
            reverse("Faq-list", kwargs={"organization_code": organization.code})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        content = response.json()
        self.assertNotEqual(organization_two.faq.title, content["title"])
        self.assertNotEqual(organization_two.faq.content, content["content"])
        self.assertEqual(organization.faq.title, content["title"])
        self.assertEqual(organization.faq.content, content["content"])

    def test_update_no_permission(self):
        fake = factories.FaqFactory.build()
        organization = factories.OrganizationFactory()
        payload = {
            "title": fake.title,
            "content": fake.content,
            "organization_code": organization.code,
        }
        self.client.force_authenticate(UserFactory())
        response = self.client.put(
            reverse("Faq-list", kwargs={"organization_code": organization.code}),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_partial_update_no_permission(self):
        organization = factories.OrganizationFactory()
        payload = {
            "title": "New title",
        }
        self.client.force_authenticate(UserFactory())
        response = self.client.patch(
            reverse("Faq-list", kwargs={"organization_code": organization.code}),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_destroy_no_permission(self):
        organization = factories.OrganizationFactory()
        self.client.force_authenticate(UserFactory())
        response = self.client.delete(
            reverse("Faq-list", kwargs={"organization_code": organization.code}),
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class FaqTestCaseBasePermission(JwtAPITestCase):
    def test_create_base_permission(self):
        fake = factories.FaqFactory.build()
        organization = factories.OrganizationFactory()
        payload = {
            "title": fake.title,
            "content": fake.content,
            "organization_code": organization.code,
        }
        user = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(user)
        response = self.client.post(
            reverse("Faq-list", kwargs={"organization_code": organization.code}),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        content = response.json()
        self.assertIn("id", content)

        faq = models.Faq.objects.get(id=content["id"])
        self.assertEqual(fake.title, faq.title)
        self.assertEqual(fake.content, faq.content)
        self.assertEqual(organization.id, faq.organization.id)
        payload["content"] = self.get_base64_image()
        response = self.client.post(
            reverse("Faq-list", kwargs={"organization_code": organization.code}),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.json())
        self.assertEqual(len(response.json()["images"]), 1)

    def test_retrieve_base_permission(self):
        organization = factories.OrganizationFactory()
        organization_two = factories.OrganizationFactory()
        user = UserFactory()
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("Faq-list", kwargs={"organization_code": organization.code})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        content = response.json()
        self.assertNotEqual(organization_two.faq.title, content["title"])
        self.assertNotEqual(organization_two.faq.content, content["content"])
        self.assertEqual(organization.faq.title, content["title"])
        self.assertEqual(organization.faq.content, content["content"])

    def test_update_base_permission(self):
        fake = factories.FaqFactory.build()
        organization = factories.OrganizationFactory()
        payload = {
            "title": "New title",
            "content": fake.content,
            "organization_code": organization.code,
        }
        user = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(user)
        response = self.client.put(
            reverse("Faq-list", kwargs={"organization_code": organization.code}),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        organization.faq.refresh_from_db()
        self.assertEqual(organization.faq.title, "New title")
        payload["content"] = self.get_base64_image()
        response = self.client.put(
            reverse("Faq-list", kwargs={"organization_code": organization.code}),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        self.assertEqual(len(response.json()["images"]), 1)

    def test_partial_update_base_permission(self):
        organization = factories.OrganizationFactory()
        payload = {
            "title": "New title",
        }
        user = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(user)
        response = self.client.patch(
            reverse("Faq-list", kwargs={"organization_code": organization.code}),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        organization.faq.refresh_from_db()
        self.assertEqual(organization.faq.title, "New title")
        payload["content"] = self.get_base64_image()
        response = self.client.patch(
            reverse("Faq-list", kwargs={"organization_code": organization.code}),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        self.assertEqual(len(response.json()["images"]), 1)

    def test_destroy_base_permission(self):
        organization = factories.OrganizationFactory()
        user = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(user)
        response = self.client.delete(
            reverse("Faq-list", kwargs={"organization_code": organization.code}),
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(models.Faq.objects.filter(id=organization.faq.id).exists())


class FaqTestCaseOrganizationPermission(JwtAPITestCase):
    def test_create_org_permission(self):
        fake = factories.FaqFactory.build()
        organization = factories.OrganizationFactory()
        payload = {
            "title": fake.title,
            "content": fake.content,
            "organization_code": organization.code,
        }
        user = UserFactory(permissions=[("organizations.add_faq", organization)])
        self.client.force_authenticate(user)
        response = self.client.post(
            reverse("Faq-list", kwargs={"organization_code": organization.code}),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        content = response.json()
        self.assertIn("id", content)
        faq = models.Faq.objects.get(id=content["id"])
        self.assertEqual(fake.title, faq.title)
        self.assertEqual(fake.content, faq.content)
        self.assertEqual(organization.id, faq.organization.id)

        payload["content"] = self.get_base64_image()
        response = self.client.post(
            reverse("Faq-list", kwargs={"organization_code": organization.code}),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.json())
        self.assertEqual(len(response.json()["images"]), 1)

    def test_retrieve_org_permission(self):
        organization = factories.OrganizationFactory()
        organization_two = factories.OrganizationFactory()
        user = UserFactory()
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("Faq-list", kwargs={"organization_code": organization.code})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        content = response.json()
        self.assertNotEqual(organization_two.faq.title, content["title"])
        self.assertNotEqual(organization_two.faq.content, content["content"])
        self.assertEqual(organization.faq.title, content["title"])
        self.assertEqual(organization.faq.content, content["content"])

    def test_update_org_permission(self):
        fake = factories.FaqFactory.build()
        organization = factories.OrganizationFactory()
        payload = {
            "title": "New title",
            "content": fake.content,
            "organization_code": organization.code,
        }
        user = UserFactory(permissions=[("organizations.change_faq", organization)])
        self.client.force_authenticate(user)
        response = self.client.put(
            reverse("Faq-list", kwargs={"organization_code": organization.code}),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        organization.faq.refresh_from_db()
        self.assertEqual(organization.faq.title, "New title")
        payload["content"] = self.get_base64_image()
        response = self.client.put(
            reverse("Faq-list", kwargs={"organization_code": organization.code}),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        self.assertEqual(len(response.json()["images"]), 1)

    def test_partial_update_org_permission(self):
        organization = factories.OrganizationFactory()
        payload = {
            "title": "New title",
        }
        user = UserFactory(permissions=[("organizations.change_faq", organization)])
        self.client.force_authenticate(user)
        response = self.client.patch(
            reverse("Faq-list", kwargs={"organization_code": organization.code}),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        organization.faq.refresh_from_db()
        self.assertEqual(organization.faq.title, "New title")

        payload["content"] = self.get_base64_image()
        response = self.client.patch(
            reverse("Faq-list", kwargs={"organization_code": organization.code}),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        self.assertEqual(len(response.json()["images"]), 1)
