import random
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.models import Group
from django.urls import reverse
from faker import Faker
from parameterized import parameterized
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.accounts.utils import get_superadmins_group
from apps.commons.test.testcases import JwtAPITestCase, TagTestCaseMixin, TestRoles
from apps.misc.models import Language
from apps.organizations.factories import OrganizationFactory
from apps.organizations.models import Organization

faker = Faker()


class CreateOrganizationTestCase(JwtAPITestCase, TagTestCaseMixin):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.parent = OrganizationFactory()
        cls.logo_image = cls.get_test_image()
        cls.users = UserFactory.create_batch(2)
        cls.facilitators = UserFactory.create_batch(2)
        cls.admins = UserFactory.create_batch(2)

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_201_CREATED),
        ]
    )
    @patch("services.wikipedia.interface.WikipediaService.wbgetentities")
    def test_create_organization(self, role, expected_code, mocked):
        mocked.side_effect = self.get_wikipedia_tag_mocked_side_effect
        wikipedia_qids = [self.get_random_wikipedia_qid() for _ in range(3)]
        user = self.get_parameterized_test_user(role, instances=[])
        self.client.force_authenticate(user)
        payload = {
            "name": faker.word(),
            "code": faker.word(),
            "dashboard_title": faker.sentence(),
            "dashboard_subtitle": faker.sentence(),
            "contact_email": faker.email(),
            "website_url": faker.url(),
            "background_color": faker.color(),
            "logo_image_id": self.logo_image.id,
            "language": random.choice(Language.values),  # nosec
            "is_logo_visible_on_parent_dashboard": faker.boolean(),
            "access_request_enabled": faker.boolean(),
            "onboarding_enabled": faker.boolean(),
            "wikipedia_tags_ids": wikipedia_qids,
            "parent_code": self.parent.code,
            "team": {
                "users": [u.id for u in self.users],
                "admins": [a.id for a in self.admins],
                "facilitators": [f.id for f in self.facilitators],
            },
        }
        response = self.client.post(reverse("Organization-list"), data=payload)
        assert response.status_code == expected_code
        if expected_code == status.HTTP_201_CREATED:
            content = response.json()
            assert content["name"] == payload["name"]
            assert content["code"] == payload["code"]
            assert content["dashboard_title"] == payload["dashboard_title"]
            assert content["dashboard_subtitle"] == payload["dashboard_subtitle"]
            assert content["contact_email"] == payload["contact_email"]
            assert content["website_url"] == payload["website_url"]
            assert content["background_color"] == payload["background_color"]
            assert content["logo_image"]["id"] == payload["logo_image_id"]
            assert content["language"] == payload["language"]
            assert (
                content["is_logo_visible_on_parent_dashboard"]
                == payload["is_logo_visible_on_parent_dashboard"]
            )
            assert content["parent_code"] == self.parent.code
            assert (
                content["access_request_enabled"] == payload["access_request_enabled"]
            )
            assert content["onboarding_enabled"] == payload["onboarding_enabled"]
            assert content["wikipedia_tags"]
            assert len(content["wikipedia_tags"]) == 3
            assert {t["wikipedia_qid"] for t in content["wikipedia_tags"]} == set(
                wikipedia_qids
            )
            organization = Organization.objects.get(code=payload["code"])
            assert all(u in organization.users.all() for u in self.users)
            assert all(a in organization.admins.all() for a in self.admins)
            assert all(f in organization.facilitators.all() for f in self.facilitators)


class ReadOrganizationTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS,),
            (TestRoles.DEFAULT,),
        ]
    )
    def test_retrieve_organization(self, role):
        user = self.get_parameterized_test_user(role, instances=[])
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("Organization-detail", args=(self.organization.code,))
        )
        assert response.status_code == status.HTTP_200_OK
        content = response.json()
        assert content["code"] == self.organization.code

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS,),
            (TestRoles.DEFAULT,),
        ]
    )
    def test_list_organization(self, role):
        user = self.get_parameterized_test_user(role, instances=[])
        self.client.force_authenticate(user)
        response = self.client.get(reverse("Organization-list"))
        assert response.status_code == status.HTTP_200_OK
        content = response.json()
        assert content["count"] == 1
        assert content["results"][0]["code"] == self.organization.code


class UpdateOrganizationTestCase(JwtAPITestCase, TagTestCaseMixin):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.logo_image = cls.get_test_image()

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_ADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_FACILITATOR, status.HTTP_200_OK),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
        ]
    )
    @patch("services.wikipedia.interface.WikipediaService.wbgetentities")
    def test_update_organization(self, role, expected_code, mocked):
        mocked.side_effect = self.get_wikipedia_tag_mocked_side_effect
        wikipedia_qids = [self.get_random_wikipedia_qid() for _ in range(3)]
        user = self.get_parameterized_test_user(role, instances=[self.organization])
        self.client.force_authenticate(user)
        payload = {
            "name": faker.word(),
            "dashboard_title": faker.sentence(),
            "dashboard_subtitle": faker.sentence(),
            "contact_email": faker.email(),
            "background_color": faker.color(),
            "logo_image_id": self.logo_image.id,
            "language": random.choice(Language.values),  # nosec
            "is_logo_visible_on_parent_dashboard": faker.boolean(),
            "access_request_enabled": faker.boolean(),
            "onboarding_enabled": faker.boolean(),
            "wikipedia_tags_ids": wikipedia_qids,
        }
        response = self.client.patch(
            reverse("Organization-detail", args=(self.organization.code,)), data=payload
        )
        assert response.status_code == expected_code
        if expected_code == status.HTTP_200_OK:
            content = response.json()
            assert content["name"] == payload["name"]
            assert content["dashboard_title"] == payload["dashboard_title"]
            assert content["dashboard_subtitle"] == payload["dashboard_subtitle"]
            assert content["contact_email"] == payload["contact_email"]
            assert content["background_color"] == payload["background_color"]
            assert content["logo_image"]["id"] == payload["logo_image_id"]
            assert content["language"] == payload["language"]
            assert (
                content["is_logo_visible_on_parent_dashboard"]
                == payload["is_logo_visible_on_parent_dashboard"]
            )
            assert (
                content["access_request_enabled"] == payload["access_request_enabled"]
            )
            assert content["onboarding_enabled"] == payload["onboarding_enabled"]
            assert content["wikipedia_tags"]
            assert {t["wikipedia_qid"] for t in content["wikipedia_tags"]} == set(
                wikipedia_qids
            )


class DeleteOrganizationTestCase(JwtAPITestCase):
    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_ADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_FACILITATOR, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_delete_organization(self, role, expected_code):
        organization = OrganizationFactory()
        user = self.get_parameterized_test_user(role, instances=[organization])
        self.client.force_authenticate(user)
        response = self.client.delete(
            reverse("Organization-detail", args=(organization.code,))
        )
        assert response.status_code == expected_code
        if expected_code == status.HTTP_204_NO_CONTENT:
            assert not Organization.objects.filter(code=organization.code).exists()


class OrganizationMembersTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.users = UserFactory.create_batch(2)
        cls.facilitators = UserFactory.create_batch(2)
        cls.admins = UserFactory.create_batch(2)

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_ADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_FACILITATOR, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_add_organization_member(self, role, expected_code):
        organization = OrganizationFactory()
        user = self.get_parameterized_test_user(role, instances=[organization])
        self.client.force_authenticate(user)
        payload = {
            "users": [u.id for u in self.users],
            "admins": [a.id for a in self.admins],
            "facilitators": [f.id for f in self.facilitators],
        }
        response = self.client.post(
            reverse("Organization-add-member", args=(organization.code,)), data=payload
        )
        assert response.status_code == expected_code
        if expected_code == status.HTTP_204_NO_CONTENT:
            assert all(u in organization.users.all() for u in self.users)
            assert all(a in organization.admins.all() for a in self.admins)
            assert all(f in organization.facilitators.all() for f in self.facilitators)

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_ADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_FACILITATOR, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_remove_project_member(self, role, expected_code):
        organization = OrganizationFactory()
        organization.users.add(*self.users)
        organization.admins.add(*self.admins)
        organization.facilitators.add(*self.facilitators)
        user = self.get_parameterized_test_user(role, instances=[organization])
        self.client.force_authenticate(user)
        payload = {
            "users": [u.id for u in self.users + self.admins + self.facilitators],
        }
        response = self.client.post(
            reverse("Organization-remove-member", args=(organization.code,)),
            data=payload,
        )
        assert response.status_code == expected_code
        if expected_code == status.HTTP_204_NO_CONTENT:
            assert all(u not in organization.users.all() for u in self.users)
            assert all(a not in organization.admins.all() for a in self.admins)
            assert all(
                f not in organization.facilitators.all() for f in self.facilitators
            )


class OrganizationHierarchyTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.parent = OrganizationFactory()
        cls.superadmin = UserFactory(groups=[get_superadmins_group()])

    def test_change_parent(self):
        self.client.force_authenticate(self.superadmin)
        organization = OrganizationFactory()
        payload = {"parent_code": self.parent.code}

        response = self.client.patch(
            reverse("Organization-detail", args=(organization.code,)),
            data=payload,
        )
        assert response.status_code == status.HTTP_200_OK
        organization.refresh_from_db()
        assert organization.parent == self.parent

    def test_set_self_as_parent(self):
        self.client.force_authenticate(self.superadmin)
        organization = OrganizationFactory()
        payload = {"parent_code": organization.code}

        response = self.client.patch(
            reverse("Organization-detail", args=(organization.code,)),
            data=payload,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        content = response.json()
        assert content["parent_code"] == [
            "You are trying to create a loop in the organization's hierarchy."
        ]

    def test_create_hierarchy_loop(self):
        self.client.force_authenticate(self.superadmin)
        organization_1 = self.parent
        organization_2 = OrganizationFactory(parent=organization_1)
        organization_3 = OrganizationFactory(parent=organization_2)
        payload = {"parent_code": organization_3.code}

        response = self.client.patch(
            reverse("Organization-detail", args=(organization_1.code,)),
            data=payload,
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        content = response.json()
        assert content["parent_code"] == [
            "You are trying to create a loop in the organization's hierarchy."
        ]

    def test_create_nested_hierarchy(self):
        self.client.force_authenticate(self.superadmin)
        organization_1 = self.parent
        organization_2 = OrganizationFactory(parent=organization_1)
        organization_3 = OrganizationFactory()
        payload = {"parent_code": organization_2.code}
        response = self.client.patch(
            reverse("Organization-detail", args=(organization_3.code,)),
            data=payload,
        )
        assert response.status_code == status.HTTP_200_OK
        organization_3.refresh_from_db()
        assert organization_3.parent == organization_2


class MiscOrganizationTestCase(JwtAPITestCase):
    def test_google_sync_enabled(self):
        organization = OrganizationFactory()
        synced_organization = OrganizationFactory(
            code=settings.GOOGLE_SYNCED_ORGANIZATION
        )

        response = self.client.get(
            reverse("Organization-detail", args=(organization.code,))
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["google_sync_enabled"] is False

        response = self.client.get(
            reverse("Organization-detail", args=(synced_organization.code,))
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["google_sync_enabled"] is True

    def test_roles_are_deleted_on_organization_delete(self):
        user = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(user)
        organization = OrganizationFactory()
        roles_names = [r.name for r in organization.groups.all()]
        response = self.client.delete(
            reverse(
                "Organization-detail",
                args=(organization.code,),
            )
        )
        assert response.status_code == 204
        assert not Group.objects.filter(name__in=roles_names).exists()
