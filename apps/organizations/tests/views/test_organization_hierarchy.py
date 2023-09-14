from django.urls import reverse
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase
from apps.organizations.factories import OrganizationFactory
from apps.organizations.models import Organization


class OrganizationHierarchyTestCase(JwtAPITestCase):
    def test_set_parent_superadmin(self):
        organization1 = OrganizationFactory()
        organization2 = OrganizationFactory()
        payload = {"parent_code": organization1.code}
        user = UserFactory()
        user.groups.add(get_superadmins_group())
        self.client.force_authenticate(user)
        response = self.client.patch(
            reverse("Organization-detail", kwargs={"code": organization2.code}),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        organization2.refresh_from_db()
        self.assertEqual(organization2.parent, organization1)

    def test_create_with_parent_superadmin(self):
        fake = OrganizationFactory.build()
        parent = OrganizationFactory()
        payload = {
            "background_color": fake.background_color,
            "code": fake.code,
            "contact_email": fake.contact_email,
            "dashboard_title": fake.dashboard_title,
            "dashboard_subtitle": fake.dashboard_subtitle,
            "language": fake.language,
            "logo_image_id": fake.logo_image.id,
            "is_logo_visible_on_parent_dashboard": fake.is_logo_visible_on_parent_dashboard,
            "name": fake.name,
            "website_url": fake.website_url,
            "created_at": fake.created_at,
            "updated_at": fake.updated_at,
            "parent_code": parent.code,
        }
        user = UserFactory()
        user.groups.add(get_superadmins_group())
        self.client.force_authenticate(user)
        response = self.client.post(reverse("Organization-list"), data=payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        organization = Organization.objects.get(id=response.json()["id"])
        self.assertEqual(organization.parent, parent)

    def test_set_parent_parent_org_permission(self):
        organization1 = OrganizationFactory()
        organization2 = OrganizationFactory()
        payload = {"parent_code": organization1.code}
        user = UserFactory(
            permissions=[("organizations.change_organization", organization1)]
        )
        self.client.force_authenticate(user)
        response = self.client.patch(
            reverse("Organization-detail", kwargs={"code": organization2.code}),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_set_parent_child_no_permission(self):
        organization1 = OrganizationFactory()
        organization2 = OrganizationFactory()
        payload = {"parent_code": organization1.code}
        self.client.force_authenticate(UserFactory())
        response = self.client.patch(
            reverse("Organization-detail", kwargs={"code": organization2.code}),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_set_parent_child_org_permission(self):
        organization1 = OrganizationFactory()
        organization2 = OrganizationFactory()
        payload = {"parent_code": organization1.code}
        user = UserFactory(
            permissions=[("organizations.change_organization", organization2)]
        )
        self.client.force_authenticate(user)
        response = self.client.patch(
            reverse("Organization-detail", kwargs={"code": organization2.code}),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        organization2.refresh_from_db()
        self.assertEqual(organization2.parent, organization1)

    def test_set_self_as_parent(self):
        organization1 = OrganizationFactory()
        payload = {"parent_code": organization1.code}
        user = UserFactory()
        user.groups.add(get_superadmins_group())
        self.client.force_authenticate(user)
        response = self.client.patch(
            reverse("Organization-detail", kwargs={"code": organization1.code}),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["parent_code"],
            ["You are trying to create a loop in the organization's hierarchy."],
        )

    def test_create_hierarchy_loop(self):
        organization1 = OrganizationFactory()
        organization2 = OrganizationFactory(parent=organization1)
        organization3 = OrganizationFactory(parent=organization2)
        payload = {"parent_code": organization3.code}
        user = UserFactory()
        user.groups.add(get_superadmins_group())
        self.client.force_authenticate(user)
        response = self.client.patch(
            reverse("Organization-detail", kwargs={"code": organization1.code}),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["parent_code"],
            ["You are trying to create a loop in the organization's hierarchy."],
        )

    def test_create_nested_hierarchy(self):
        organization1 = OrganizationFactory()
        organization2 = OrganizationFactory(parent=organization1)
        organization3 = OrganizationFactory()
        payload = {"parent_code": organization2.code}
        user = UserFactory()
        user.groups.add(get_superadmins_group())
        self.client.force_authenticate(user)
        response = self.client.patch(
            reverse("Organization-detail", kwargs={"code": organization3.code}),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        organization3.refresh_from_db()
        self.assertEqual(organization3.parent, organization2)
