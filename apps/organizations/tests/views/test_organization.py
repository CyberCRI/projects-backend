import random
from functools import reduce

from django.conf import settings
from django.contrib.auth.models import Group
from django.urls import reverse
from faker import Faker
from parameterized import parameterized
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.accounts.models import PeopleGroup
from apps.accounts.utils import get_superadmins_group
from apps.commons.enums import Language
from apps.commons.test import JwtAPITestCase, TestRoles
from apps.organizations.factories import OrganizationFactory
from apps.organizations.models import Organization
from apps.projects.factories import ProjectFactory
from apps.projects.models import Project
from apps.skills.factories import TagClassificationFactory, TagFactory
from apps.skills.models import TagClassification

faker = Faker()


class CreateOrganizationTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.parent = OrganizationFactory()
        cls.logo_image = cls.get_test_image()
        cls.users = UserFactory.create_batch(2)
        cls.facilitators = UserFactory.create_batch(2)
        cls.admins = UserFactory.create_batch(2)
        cls.default_projects_tags = TagFactory.create_batch(2)
        cls.default_skills_tags = TagFactory.create_batch(2)
        cls.projects_tag_classification = (
            TagClassification.get_or_create_default_classification(
                TagClassification.TagClassificationType.WIKIPEDIA
            )
        )
        cls.skills_tag_classification = (
            TagClassification.get_or_create_default_classification(
                TagClassification.TagClassificationType.ESCO
            )
        )

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_201_CREATED),
        ]
    )
    def test_create_organization(self, role, expected_code):
        user = self.get_parameterized_test_user(role, instances=[])
        self.client.force_authenticate(user)
        language = random.choice(Language.values)  # nosec
        payload = {
            "name": faker.word(),
            "code": faker.word(),
            "dashboard_title": faker.sentence(),
            "dashboard_subtitle": faker.sentence(),
            "description": faker.text(),
            "contact_email": faker.email(),
            "chat_url": faker.url(),
            "chat_button_text": faker.word(),
            "website_url": faker.url(),
            "background_color": faker.color(),
            "logo_image_id": self.logo_image.id,
            "language": language,
            "languages": list(set([language, random.choice(Language.values)])),  # nosec
            "is_logo_visible_on_parent_dashboard": faker.boolean(),
            "access_request_enabled": faker.boolean(),
            "onboarding_enabled": faker.boolean(),
            "force_login_form_display": faker.boolean(),
            "parent_code": self.parent.code,
            "team": {
                "users": [u.id for u in self.users],
                "admins": [a.id for a in self.admins],
                "facilitators": [f.id for f in self.facilitators],
            },
            "enabled_projects_tag_classifications": [
                self.projects_tag_classification.id
            ],
            "default_projects_tag_classification": self.projects_tag_classification.id,
            "enabled_skills_tag_classifications": [self.skills_tag_classification.id],
            "default_skills_tag_classification": self.skills_tag_classification.id,
            "default_projects_tags": [t.id for t in self.default_projects_tags],
            "default_skills_tags": [t.id for t in self.default_skills_tags],
        }
        response = self.client.post(reverse("Organization-list"), data=payload)
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_201_CREATED:
            content = response.json()
            self.assertEqual(content["name"], payload["name"])
            self.assertEqual(content["code"], payload["code"])
            self.assertEqual(content["dashboard_title"], payload["dashboard_title"])
            self.assertEqual(
                content["dashboard_subtitle"], payload["dashboard_subtitle"]
            )
            self.assertEqual(content["description"], payload["description"])
            self.assertEqual(content["contact_email"], payload["contact_email"])
            self.assertEqual(content["chat_url"], payload["chat_url"])
            self.assertEqual(content["chat_button_text"], payload["chat_button_text"])
            self.assertEqual(content["website_url"], payload["website_url"])
            self.assertEqual(content["background_color"], payload["background_color"])
            self.assertEqual(content["logo_image"]["id"], payload["logo_image_id"])
            self.assertEqual(content["language"], payload["language"])
            self.assertSetEqual(set(content["languages"]), set(payload["languages"]))
            self.assertEqual(
                content["is_logo_visible_on_parent_dashboard"],
                payload["is_logo_visible_on_parent_dashboard"],
            )
            self.assertEqual(content["parent_code"], self.parent.code)
            self.assertEqual(
                content["access_request_enabled"], payload["access_request_enabled"]
            )
            self.assertEqual(
                content["onboarding_enabled"], payload["onboarding_enabled"]
            )
            self.assertEqual(
                content["force_login_form_display"], payload["force_login_form_display"]
            )
            self.assertSetEqual(
                {c["id"] for c in content["enabled_projects_tag_classifications"]},
                {self.projects_tag_classification.id},
            )
            self.assertEqual(
                content["default_projects_tag_classification"]["id"],
                self.projects_tag_classification.id,
            )
            self.assertSetEqual(
                {c["id"] for c in content["enabled_skills_tag_classifications"]},
                {self.skills_tag_classification.id},
            )
            self.assertEqual(
                content["default_skills_tag_classification"]["id"],
                self.skills_tag_classification.id,
            )
            self.assertSetEqual(
                {t["id"] for t in content["default_projects_tags"]},
                {t.id for t in self.default_projects_tags},
            )
            self.assertSetEqual(
                {t["id"] for t in content["default_skills_tags"]},
                {t.id for t in self.default_skills_tags},
            )
            organization = Organization.objects.get(code=payload["code"])
            for user in self.users:
                self.assertIn(user, organization.users.all())
            for admin in self.admins:
                self.assertIn(admin, organization.admins.all())
            for facilitator in self.facilitators:
                self.assertIn(facilitator, organization.facilitators.all())


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
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["code"], self.organization.code)

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
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["code"], self.organization.code)


class UpdateOrganizationTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.logo_image = cls.get_test_image()
        cls.default_projects_tags = TagFactory.create_batch(2)
        cls.default_skills_tags = TagFactory.create_batch(2)
        cls.projects_tag_classification = TagClassificationFactory(
            organization=cls.organization
        )
        cls.skills_tag_classification = TagClassificationFactory(
            organization=cls.organization
        )

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
    def test_update_organization(self, role, expected_code):
        user = self.get_parameterized_test_user(role, instances=[self.organization])
        self.client.force_authenticate(user)
        payload = {
            "name": faker.word(),
            "dashboard_title": faker.sentence(),
            "dashboard_subtitle": faker.sentence(),
            "description": faker.text(),
            "contact_email": faker.email(),
            "chat_url": faker.url(),
            "chat_button_text": faker.word(),
            "background_color": faker.color(),
            "logo_image_id": self.logo_image.id,
            "language": random.choice(Language.values),  # nosec
            "is_logo_visible_on_parent_dashboard": faker.boolean(),
            "access_request_enabled": faker.boolean(),
            "onboarding_enabled": faker.boolean(),
            "force_login_form_display": faker.boolean(),
            "enabled_projects_tag_classifications": [
                self.projects_tag_classification.id
            ],
            "default_projects_tag_classification": self.projects_tag_classification.id,
            "enabled_skills_tag_classifications": [self.skills_tag_classification.id],
            "default_skills_tag_classification": self.skills_tag_classification.id,
            "default_projects_tags": [t.id for t in self.default_projects_tags],
            "default_skills_tags": [t.id for t in self.default_skills_tags],
        }
        response = self.client.patch(
            reverse("Organization-detail", args=(self.organization.code,)), data=payload
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_200_OK:
            content = response.json()
            self.assertEqual(content["name"], payload["name"])
            self.assertEqual(content["dashboard_title"], payload["dashboard_title"])
            self.assertEqual(
                content["dashboard_subtitle"], payload["dashboard_subtitle"]
            )
            self.assertEqual(content["description"], payload["description"])
            self.assertEqual(content["contact_email"], payload["contact_email"])
            self.assertEqual(content["chat_url"], payload["chat_url"])
            self.assertEqual(content["chat_button_text"], payload["chat_button_text"])
            self.assertEqual(content["background_color"], payload["background_color"])
            self.assertEqual(content["logo_image"]["id"], payload["logo_image_id"])
            self.assertEqual(content["language"], payload["language"])
            self.assertEqual(
                content["is_logo_visible_on_parent_dashboard"],
                payload["is_logo_visible_on_parent_dashboard"],
            )
            self.assertEqual(
                content["access_request_enabled"], payload["access_request_enabled"]
            )
            self.assertEqual(
                content["onboarding_enabled"], payload["onboarding_enabled"]
            )
            self.assertEqual(
                content["force_login_form_display"], payload["force_login_form_display"]
            )
            self.assertSetEqual(
                {c["id"] for c in content["enabled_projects_tag_classifications"]},
                {self.projects_tag_classification.id},
            )
            self.assertEqual(
                content["default_projects_tag_classification"]["id"],
                self.projects_tag_classification.id,
            )
            self.assertSetEqual(
                {c["id"] for c in content["enabled_skills_tag_classifications"]},
                {self.skills_tag_classification.id},
            )
            self.assertEqual(
                content["default_skills_tag_classification"]["id"],
                self.skills_tag_classification.id,
            )
            self.assertSetEqual(
                {t["id"] for t in content["default_projects_tags"]},
                {t.id for t in self.default_projects_tags},
            )
            self.assertSetEqual(
                {t["id"] for t in content["default_skills_tags"]},
                {t.id for t in self.default_skills_tags},
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
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_204_NO_CONTENT:
            self.assertFalse(
                Organization.objects.filter(code=organization.code).exists()
            )


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
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_204_NO_CONTENT:
            for user in self.users:
                self.assertIn(user, organization.users.all())
            for admin in self.admins:
                self.assertIn(admin, organization.admins.all())
            for facilitator in self.facilitators:
                self.assertIn(facilitator, organization.facilitators.all())

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
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_204_NO_CONTENT:
            for user in self.users:
                self.assertNotIn(user, organization.users.all())
            for admin in self.admins:
                self.assertNotIn(admin, organization.admins.all())
            for facilitator in self.facilitators:
                self.assertNotIn(facilitator, organization.facilitators.all())


class OrganizationFeaturedProjectTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        ProjectFactory(organizations=[cls.organization])
        cls.projects = {
            "public": ProjectFactory(
                publication_status=Project.PublicationStatus.PUBLIC,
                organizations=[cls.organization],
            ),
            "private": ProjectFactory(
                publication_status=Project.PublicationStatus.PRIVATE,
                organizations=[cls.organization],
            ),
            "org": ProjectFactory(
                publication_status=Project.PublicationStatus.ORG,
                organizations=[cls.organization],
            ),
        }

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
    def test_add_featured_project(self, role, expected_code):
        organization = self.organization
        projects = self.projects
        user = self.get_parameterized_test_user(role, instances=[organization])
        self.client.force_authenticate(user)
        payload = {"featured_projects_ids": [p.pk for p in projects.values()]}
        response = self.client.post(
            reverse(
                "Organization-add-featured-project",
                args=([organization.code]),
            ),
            payload,
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_204_NO_CONTENT:
            featured_projects = [
                project.id for project in organization.featured_projects.all()
            ]
            for project in projects.values():
                self.assertIn(project.id, featured_projects)

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
    def test_remove_featured_project(self, role, expected_code):
        organization = self.organization
        projects = self.projects
        user = self.get_parameterized_test_user(role, instances=[organization])
        self.client.force_authenticate(user)
        payload = {"featured_projects_ids": [p.pk for p in projects.values()]}
        response = self.client.post(
            reverse(
                "Organization-remove-featured-project",
                args=([organization.code]),
            ),
            payload,
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_204_NO_CONTENT:
            for project in projects.values():
                self.assertNotIn(project, organization.featured_projects.all())

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, ("public",)),
            (TestRoles.DEFAULT, ("public",)),
            (TestRoles.SUPERADMIN, ("public", "private", "org")),
            (TestRoles.ORG_ADMIN, ("public", "private", "org")),
            (TestRoles.ORG_FACILITATOR, ("public", "private", "org")),
            (TestRoles.ORG_USER, ("public", "org")),
        ]
    )
    def test_retrieve_featured_projects(self, role, retrieved_projects):
        organization = self.organization
        projects = self.projects
        organization.featured_projects.add(*projects.values())
        user = self.get_parameterized_test_user(role, instances=[organization])
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("Organization-featured-project", args=([organization.code]))
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), len(retrieved_projects))
        self.assertEqual(
            {p["id"] for p in content},
            {projects[p].id for p in retrieved_projects},
        )


class OrganizationPeopleGroupsHierarchyTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.root_group = PeopleGroup.update_or_create_root(cls.organization)

        cls.level_1_public = PeopleGroup.objects.create(
            organization=cls.organization,
            parent=cls.root_group,
            publication_status=PeopleGroup.PublicationStatus.PUBLIC,
        )
        cls.level_1_org = PeopleGroup.objects.create(
            organization=cls.organization,
            parent=cls.root_group,
            publication_status=PeopleGroup.PublicationStatus.ORG,
        )
        cls.level_1_private = PeopleGroup.objects.create(
            organization=cls.organization,
            parent=cls.root_group,
            publication_status=PeopleGroup.PublicationStatus.PRIVATE,
        )

        cls.level_2_public_public = PeopleGroup.objects.create(
            organization=cls.organization,
            parent=cls.level_1_public,
            publication_status=PeopleGroup.PublicationStatus.PUBLIC,
        )
        cls.level_2_public_org = PeopleGroup.objects.create(
            organization=cls.organization,
            parent=cls.level_1_public,
            publication_status=PeopleGroup.PublicationStatus.ORG,
        )
        cls.level_2_public_private = PeopleGroup.objects.create(
            organization=cls.organization,
            parent=cls.level_1_public,
            publication_status=PeopleGroup.PublicationStatus.PRIVATE,
        )

        cls.level_2_org_public = PeopleGroup.objects.create(
            organization=cls.organization,
            parent=cls.level_1_org,
            publication_status=PeopleGroup.PublicationStatus.PUBLIC,
        )
        cls.level_2_org_org = PeopleGroup.objects.create(
            organization=cls.organization,
            parent=cls.level_1_org,
            publication_status=PeopleGroup.PublicationStatus.ORG,
        )
        cls.level_2_org_private = PeopleGroup.objects.create(
            organization=cls.organization,
            parent=cls.level_1_org,
            publication_status=PeopleGroup.PublicationStatus.PRIVATE,
        )

        cls.level_2_private_public = PeopleGroup.objects.create(
            organization=cls.organization,
            parent=cls.level_1_private,
            publication_status=PeopleGroup.PublicationStatus.PUBLIC,
        )
        cls.level_2_private_org = PeopleGroup.objects.create(
            organization=cls.organization,
            parent=cls.level_1_private,
            publication_status=PeopleGroup.PublicationStatus.ORG,
        )
        cls.level_2_private_private = PeopleGroup.objects.create(
            organization=cls.organization,
            parent=cls.level_1_private,
            publication_status=PeopleGroup.PublicationStatus.PRIVATE,
        )

        cls.groups = {
            "root": cls.root_group,
            "level_1_public": cls.level_1_public,
            "level_1_org": cls.level_1_org,
            "level_1_private": cls.level_1_private,
            "level_2_public_public": cls.level_2_public_public,
            "level_2_public_org": cls.level_2_public_org,
            "level_2_public_private": cls.level_2_public_private,
            "level_2_org_public": cls.level_2_org_public,
            "level_2_org_org": cls.level_2_org_org,
            "level_2_org_private": cls.level_2_org_private,
            "level_2_private_public": cls.level_2_private_public,
            "level_2_private_org": cls.level_2_private_org,
            "level_2_private_private": cls.level_2_private_private,
        }

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, ("root", "level_1_public", "level_2_public_public")),
            (TestRoles.DEFAULT, ("root", "level_1_public", "level_2_public_public")),
            (
                TestRoles.SUPERADMIN,
                (
                    "root",
                    "level_1_public",
                    "level_1_org",
                    "level_1_private",
                    "level_2_public_public",
                    "level_2_public_org",
                    "level_2_public_private",
                    "level_2_org_public",
                    "level_2_org_org",
                    "level_2_org_private",
                    "level_2_private_public",
                    "level_2_private_org",
                    "level_2_private_private",
                ),
            ),
            (
                TestRoles.ORG_ADMIN,
                (
                    "root",
                    "level_1_public",
                    "level_1_org",
                    "level_1_private",
                    "level_2_public_public",
                    "level_2_public_org",
                    "level_2_public_private",
                    "level_2_org_public",
                    "level_2_org_org",
                    "level_2_org_private",
                    "level_2_private_public",
                    "level_2_private_org",
                    "level_2_private_private",
                ),
            ),
            (
                TestRoles.ORG_FACILITATOR,
                (
                    "root",
                    "level_1_public",
                    "level_1_org",
                    "level_1_private",
                    "level_2_public_public",
                    "level_2_public_org",
                    "level_2_public_private",
                    "level_2_org_public",
                    "level_2_org_org",
                    "level_2_org_private",
                    "level_2_private_public",
                    "level_2_private_org",
                    "level_2_private_private",
                ),
            ),
            (
                TestRoles.ORG_USER,
                (
                    "root",
                    "level_1_public",
                    "level_1_org",
                    "level_2_public_public",
                    "level_2_public_org",
                    "level_2_org_public",
                    "level_2_org_org",
                ),
            ),
            (
                TestRoles.GROUP_LEADER,
                (
                    "root",
                    "level_1_public",
                    "level_1_private",
                    "level_2_public_public",
                    "level_2_public_private",
                    "level_2_private_public",
                    "level_2_private_private",
                ),
            ),
            (
                TestRoles.GROUP_MANAGER,
                (
                    "root",
                    "level_1_public",
                    "level_1_private",
                    "level_2_public_public",
                    "level_2_public_private",
                    "level_2_private_public",
                    "level_2_private_private",
                ),
            ),
            (
                TestRoles.GROUP_MEMBER,
                (
                    "root",
                    "level_1_public",
                    "level_1_private",
                    "level_2_public_public",
                    "level_2_public_private",
                    "level_2_private_public",
                    "level_2_private_private",
                ),
            ),
        ]
    )
    def test_retrieve_organization_people_groups_hierarchy(self, role, expected_groups):
        organization = self.organization
        groups = self.groups
        user = self.get_parameterized_test_user(
            role,
            instances=[
                self.level_1_private,
                self.level_2_public_private,
                self.level_2_private_private,
                self.level_2_org_private,
            ],
        )
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("Organization-people-groups-hierarchy", args=([organization.code]))
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        groups = [response.json()]
        retrieved_groups = []
        while groups:
            retrieved_groups += [g["id"] for g in groups]
            groups = reduce(lambda x, y: x + y["children"], groups, [])

        self.assertSetEqual(
            set(retrieved_groups), {self.groups[g].id for g in expected_groups}
        )


class ValidateOrganizationTestCase(JwtAPITestCase):
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
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        organization.refresh_from_db()
        self.assertEqual(organization.parent, self.parent)

    def test_set_self_as_parent(self):
        self.client.force_authenticate(self.superadmin)
        organization = OrganizationFactory()
        payload = {"parent_code": organization.code}

        response = self.client.patch(
            reverse("Organization-detail", args=(organization.code,)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertApiValidationError(
            response,
            {
                "parent_code": [
                    "You are trying to create a loop in the organization's hierarchy."
                ]
            },
        )

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
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertApiValidationError(
            response,
            {
                "parent_code": [
                    "You are trying to create a loop in the organization's hierarchy."
                ]
            },
        )

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
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        organization_3.refresh_from_db()
        self.assertEqual(organization_3.parent, organization_2)

    def test_create_with_not_enabled_default_projects_tag_classification(self):
        self.client.force_authenticate(self.superadmin)
        tag_classification = TagClassification.get_or_create_default_classification(
            TagClassification.TagClassificationType.WIKIPEDIA
        )
        payload = {
            "name": faker.word(),
            "code": faker.word(),
            "dashboard_title": faker.sentence(),
            "dashboard_subtitle": faker.sentence(),
            "logo_image_id": self.get_test_image().id,
            "parent_code": self.parent.code,
            "website_url": faker.url(),
            "enabled_projects_tag_classifications": [],
            "default_projects_tag_classification": tag_classification.id,
        }
        response = self.client.post(reverse("Organization-list"), data=payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertApiValidationError(
            response,
            {
                "default_projects_tag_classification": [
                    "You must choose a default tag classification that is enabled"
                ]
            },
        )

    def test_update_with_not_enabled_default_projects_tag_classification(self):
        self.client.force_authenticate(self.superadmin)
        organization = OrganizationFactory()
        tag_classification = TagClassification.get_or_create_default_classification(
            TagClassification.TagClassificationType.WIKIPEDIA
        )
        payload = {
            "default_projects_tag_classification": tag_classification.id,
        }
        response = self.client.patch(
            reverse("Organization-detail", args=(organization.code,)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertApiValidationError(
            response,
            {
                "default_projects_tag_classification": [
                    "You must choose a default tag classification that is enabled"
                ]
            },
        )

    def test_update_with_removed_enable_default_projects_tag_classification(self):
        self.client.force_authenticate(self.superadmin)
        organization = OrganizationFactory()
        tag_classification = TagClassification.get_or_create_default_classification(
            TagClassification.TagClassificationType.WIKIPEDIA
        )
        organization.enabled_projects_tag_classifications.add(tag_classification)
        payload = {
            "enabled_projects_tag_classifications": [],
            "default_projects_tag_classification": tag_classification.id,
        }
        response = self.client.patch(
            reverse("Organization-detail", args=(organization.code,)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertApiValidationError(
            response,
            {
                "default_projects_tag_classification": [
                    "You must choose a default tag classification that is enabled"
                ]
            },
        )

    def test_create_with_not_enabled_default_skills_tag_classification(self):
        self.client.force_authenticate(self.superadmin)
        tag_classification = TagClassification.get_or_create_default_classification(
            TagClassification.TagClassificationType.WIKIPEDIA
        )
        payload = {
            "name": faker.word(),
            "code": faker.word(),
            "dashboard_title": faker.sentence(),
            "dashboard_subtitle": faker.sentence(),
            "logo_image_id": self.get_test_image().id,
            "parent_code": self.parent.code,
            "website_url": faker.url(),
            "enabled_skills_tag_classifications": [],
            "default_skills_tag_classification": tag_classification.id,
        }
        response = self.client.post(reverse("Organization-list"), data=payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertApiValidationError(
            response,
            {
                "default_skills_tag_classification": [
                    "You must choose a default tag classification that is enabled"
                ]
            },
        )

    def test_update_with_not_enabled_default_skills_tag_classification(self):
        self.client.force_authenticate(self.superadmin)
        organization = OrganizationFactory()
        tag_classification = TagClassification.get_or_create_default_classification(
            TagClassification.TagClassificationType.WIKIPEDIA
        )
        payload = {
            "default_skills_tag_classification": tag_classification.id,
        }
        response = self.client.patch(
            reverse("Organization-detail", args=(organization.code,)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertApiValidationError(
            response,
            {
                "default_skills_tag_classification": [
                    "You must choose a default tag classification that is enabled"
                ]
            },
        )

    def test_update_with_removed_enable_default_skills_tag_classification(self):
        self.client.force_authenticate(self.superadmin)
        organization = OrganizationFactory()
        tag_classification = TagClassification.get_or_create_default_classification(
            TagClassification.TagClassificationType.WIKIPEDIA
        )
        organization.enabled_skills_tag_classifications.add(tag_classification)
        payload = {
            "enabled_skills_tag_classifications": [],
            "default_skills_tag_classification": tag_classification.id,
        }
        response = self.client.patch(
            reverse("Organization-detail", args=(organization.code,)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertApiValidationError(
            response,
            {
                "default_skills_tag_classification": [
                    "You must choose a default tag classification that is enabled"
                ]
            },
        )


class MiscOrganizationTestCase(JwtAPITestCase):
    def test_google_sync_enabled(self):
        organization = OrganizationFactory()
        synced_organization = OrganizationFactory(
            code=settings.GOOGLE_SYNCED_ORGANIZATION
        )

        response = self.client.get(
            reverse("Organization-detail", args=(organization.code,))
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.json()["google_sync_enabled"])

        response = self.client.get(
            reverse("Organization-detail", args=(synced_organization.code,))
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.json()["google_sync_enabled"])

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
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Group.objects.filter(name__in=roles_names).exists())

    def test_add_enabled_tag_classifications_with_slug(self):
        user = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(user)
        organization = OrganizationFactory()
        tag_classification = TagClassificationFactory(organization=organization)
        tag_classification_2 = TagClassificationFactory(organization=organization)
        payload = {
            "enabled_projects_tag_classifications": [
                tag_classification.slug,
                tag_classification_2.id,
            ],
            "enabled_skills_tag_classifications": [
                tag_classification.slug,
                tag_classification_2.id,
            ],
        }
        response = self.client.patch(
            reverse("Organization-detail", args=(organization.code,)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(
            {c["id"] for c in content["enabled_projects_tag_classifications"]},
            {tag_classification.id, tag_classification_2.id},
        )
        self.assertEqual(
            {c["id"] for c in content["enabled_skills_tag_classifications"]},
            {tag_classification.id, tag_classification_2.id},
        )
