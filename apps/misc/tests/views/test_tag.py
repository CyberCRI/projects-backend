from django.urls import reverse
from faker import Faker

from apps.accounts.factories import UserFactory
from apps.commons.test import JwtAPITestCase
from apps.misc.factories import TagFactory
from apps.organizations.factories import OrganizationFactory

fake = Faker()


class ProjectTestCaseAnonymous(JwtAPITestCase):
    def test_create_anonymous(self):
        response = self.client.post(
            reverse("Tag-list"),
            {"name": fake.word(), "organization": OrganizationFactory().code},
        )
        self.assertEqual(response.status_code, 401)

    def test_retrieve_anonymous(self):
        tag = TagFactory()
        response = self.client.get(reverse("Tag-detail", args=[tag.id]))
        self.assertEqual(response.status_code, 200)

    def test_list_anonymous(self):
        organization = OrganizationFactory()
        TagFactory.create_batch(size=5, organization=organization)
        TagFactory.create_batch(size=5, organization=OrganizationFactory())
        response = self.client.get(
            reverse("Tag-list"), {"organization": organization.code}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 5)

    def test_update_anonymous(self):
        organization = OrganizationFactory()
        tag = TagFactory(organization=organization)
        response = self.client.put(
            reverse("Tag-detail", args=[tag.id]),
            {"name": "NewName", "organization": organization.code},
        )
        self.assertEqual(response.status_code, 401)

    def test_partial_update_anonymous(self):
        organization = OrganizationFactory()
        tag = TagFactory(organization=organization)
        response = self.client.patch(
            reverse("Tag-detail", args=[tag.id]),
            {"name": "NewName"},
        )
        self.assertEqual(response.status_code, 401)

    def test_destroy_anonymous(self):
        organization = OrganizationFactory()
        tag = TagFactory(organization=organization)
        response = self.client.delete(reverse("Tag-detail", args=[tag.id]))
        self.assertEqual(response.status_code, 401)


class ProjectTestCaseNoPermission(JwtAPITestCase):
    def test_create_no_permission(self):
        self.client.force_authenticate(UserFactory())
        response = self.client.post(
            reverse("Tag-list"),
            {"name": fake.word(), "organization": OrganizationFactory().code},
        )
        self.assertEqual(response.status_code, 403)

    def test_update_no_permission(self):
        self.client.force_authenticate(UserFactory())
        organization = OrganizationFactory()
        tag = TagFactory(organization=organization)
        response = self.client.put(
            reverse("Tag-detail", args=[tag.id]),
            {"name": "NewName", "organization": organization.code},
        )
        self.assertEqual(response.status_code, 403)

    def test_partial_update_no_permission(self):
        self.client.force_authenticate(UserFactory())
        tag = TagFactory()
        response = self.client.patch(
            reverse("Tag-detail", args=[tag.id]),
            {"name": "NewName"},
        )
        self.assertEqual(response.status_code, 403)

    def test_destroy_no_permission(self):
        self.client.force_authenticate(UserFactory())
        organization = OrganizationFactory()
        tag = TagFactory(organization=organization)
        response = self.client.delete(reverse("Tag-detail", args=[tag.id]))
        self.assertEqual(response.status_code, 403)


class ProjectTestCaseBasePermission(JwtAPITestCase):
    def test_create_base_permission(self):
        user = UserFactory(permissions=[("misc.add_tag", None)])
        self.client.force_authenticate(user)
        organization = OrganizationFactory()
        response = self.client.post(
            reverse("Tag-list"),
            {"name": "NewName", "organization": organization.code},
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["name"], "NewName")
        self.assertEqual(response.json()["organization"], organization.code)

    def test_update_base_permission(self):
        user = UserFactory(permissions=[("misc.change_tag", None)])
        self.client.force_authenticate(user)
        organization = OrganizationFactory()
        tag = TagFactory(organization=organization)
        response = self.client.put(
            reverse("Tag-detail", args=[tag.id]),
            {"name": "NewName", "organization": organization.code},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["name"], "NewName")

    def test_partial_update_base_permission(self):
        user = UserFactory(permissions=[("misc.change_tag", None)])
        self.client.force_authenticate(user)
        tag = TagFactory()
        response = self.client.patch(
            reverse("Tag-detail", args=[tag.id]),
            {"name": "NewName"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["name"], "NewName")

    def test_destroy_base_permission(self):
        user = UserFactory(permissions=[("misc.delete_tag", None)])
        self.client.force_authenticate(user)
        organization = OrganizationFactory()
        tag = TagFactory(organization=organization)
        response = self.client.delete(reverse("Tag-detail", args=[tag.id]))
        self.assertEqual(response.status_code, 204)


class ProjectTestCaseOrgPermission(JwtAPITestCase):
    def test_create_org_permission(self):
        organization = OrganizationFactory()
        user = UserFactory(permissions=[("organizations.add_tag", organization)])
        self.client.force_authenticate(user)
        response = self.client.post(
            reverse("Tag-list"),
            {"name": "Name", "organization": organization.code},
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["name"], "Name")
        self.assertEqual(response.json()["organization"], organization.code)

    def test_update_org_permission(self):
        organization = OrganizationFactory()
        user = UserFactory(permissions=[("organizations.change_tag", organization)])
        self.client.force_authenticate(user)
        tag = TagFactory(organization=organization)
        response = self.client.put(
            reverse("Tag-detail", args=[tag.id]),
            {"name": "NewName", "organization": organization.code},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["name"], "NewName")

    def test_partial_update_org_permission(self):
        organization = OrganizationFactory()
        user = UserFactory(permissions=[("organizations.change_tag", organization)])
        self.client.force_authenticate(user)
        tag = TagFactory(organization=organization)
        response = self.client.patch(
            reverse("Tag-detail", args=[tag.id]),
            {"name": "NewName"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["name"], "NewName")

    def test_destroy_org_permission(self):
        organization = OrganizationFactory()
        user = UserFactory(permissions=[("organizations.delete_tag", organization)])
        self.client.force_authenticate(user)
        tag = TagFactory(organization=organization)
        response = self.client.delete(reverse("Tag-detail", args=[tag.id]))
        self.assertEqual(response.status_code, 204)
