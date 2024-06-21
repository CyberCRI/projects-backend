from django.contrib.auth.models import Group
from django.urls import reverse
from faker import Faker
from parameterized import parameterized
from rest_framework import status

from apps.accounts.factories import PeopleGroupFactory, UserFactory
from apps.accounts.models import PeopleGroup
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase, TestRoles
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory
from apps.projects.models import Project

faker = Faker()


class CreatePeopleGroupTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.parent = PeopleGroupFactory(organization=cls.organization)
        cls.members = UserFactory.create_batch(3)
        cls.managers = UserFactory.create_batch(3)
        cls.leaders = UserFactory.create_batch(3)
        cls.projects = ProjectFactory.create_batch(3)

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_201_CREATED),
            (TestRoles.ORG_ADMIN, status.HTTP_201_CREATED),
            (TestRoles.ORG_FACILITATOR, status.HTTP_201_CREATED),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_create_people_group(self, role, expected_code):
        organization = self.organization
        parent = self.parent
        members = self.members
        managers = self.managers
        leaders = self.leaders
        projects = self.projects
        user = self.get_parameterized_test_user(role, instances=[organization])
        self.client.force_authenticate(user)
        payload = {
            "name": faker.name(),
            "description": faker.text(),
            "email": faker.email(),
            "parent": parent.id,
            "team": {
                "members": [m.id for m in members],
                "managers": [r.id for r in managers],
                "leaders": [r.id for r in leaders],
            },
            "featured_projects": [p.pk for p in projects],
        }
        response = self.client.post(
            reverse("PeopleGroup-list", args=(organization.code,)),
            payload,
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_201_CREATED:
            self.assertEqual(response.data["name"], payload["name"])
            self.assertEqual(response.data["description"], payload["description"])
            self.assertEqual(response.data["email"], payload["email"])
            self.assertEqual(response.data["organization"], organization.code)
            self.assertEqual(response.data["hierarchy"][0]["id"], parent.id)
            self.assertEqual(response.data["hierarchy"][0]["slug"], parent.slug)
            people_group = PeopleGroup.objects.get(id=response.json()["id"])
            for member in members:
                self.assertIn(member, people_group.members.all())
            for manager in managers:
                self.assertIn(manager, people_group.managers.all())
            for leader in leaders:
                self.assertIn(leader, people_group.leaders.all())
            for project in projects:
                self.assertIn(project, people_group.featured_projects.all())


class UpdatePeopleGroupTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.people_group = PeopleGroupFactory(organization=cls.organization)

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_ADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_FACILITATOR, status.HTTP_200_OK),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
            (TestRoles.GROUP_LEADER, status.HTTP_200_OK),
            (TestRoles.GROUP_MANAGER, status.HTTP_200_OK),
            (TestRoles.GROUP_MEMBER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_update_people_group(self, role, expected_code):
        user = self.get_parameterized_test_user(role, instances=[self.people_group])
        self.client.force_authenticate(user)
        payload = {
            "description": faker.text(),
        }
        response = self.client.patch(
            reverse(
                "PeopleGroup-detail",
                args=(self.organization.code, self.people_group.pk),
            ),
            payload,
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_200_OK:
            self.assertEqual(response.data["description"], payload["description"])


class DeletePeopleGroupTestCase(JwtAPITestCase):
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
            (TestRoles.ORG_FACILITATOR, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
            (TestRoles.GROUP_LEADER, status.HTTP_204_NO_CONTENT),
            (TestRoles.GROUP_MANAGER, status.HTTP_204_NO_CONTENT),
            (TestRoles.GROUP_MEMBER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_delete_people_group(self, role, expected_code):
        organization = self.organization
        people_group = PeopleGroupFactory(organization=organization)
        user = self.get_parameterized_test_user(role, instances=[people_group])
        self.client.force_authenticate(user)
        response = self.client.delete(
            reverse(
                "PeopleGroup-detail",
                args=(organization.code, people_group.pk),
            ),
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_204_NO_CONTENT:
            self.assertFalse(PeopleGroup.objects.filter(id=people_group.id).exists())


class PeopleGroupMemberTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.members = UserFactory.create_batch(3)
        cls.managers = UserFactory.create_batch(3)
        cls.leaders = UserFactory.create_batch(3)

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_ADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_FACILITATOR, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
            (TestRoles.GROUP_LEADER, status.HTTP_204_NO_CONTENT),
            (TestRoles.GROUP_MANAGER, status.HTTP_204_NO_CONTENT),
            (TestRoles.GROUP_MEMBER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_add_people_group_member(self, role, expected_code):
        organization = self.organization
        members = self.members
        managers = self.managers
        leaders = self.leaders
        people_group = PeopleGroupFactory(organization=organization)
        user = self.get_parameterized_test_user(role, instances=[people_group])
        self.client.force_authenticate(user)
        payload = {
            "members": [m.id for m in members],
            "managers": [r.id for r in managers],
            "leaders": [r.id for r in leaders],
        }
        response = self.client.post(
            reverse(
                "PeopleGroup-add-member",
                args=(organization.code, people_group.pk),
            ),
            payload,
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_204_NO_CONTENT:
            for member in members:
                self.assertIn(member, people_group.members.all())
            for manager in managers:
                self.assertIn(manager, people_group.managers.all())
            for leader in leaders:
                self.assertIn(leader, people_group.leaders.all())

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_ADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_FACILITATOR, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
            (TestRoles.GROUP_LEADER, status.HTTP_204_NO_CONTENT),
            (TestRoles.GROUP_MANAGER, status.HTTP_204_NO_CONTENT),
            (TestRoles.GROUP_MEMBER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_remove_people_group_member(self, role, expected_code):
        organization = self.organization
        members = self.members
        managers = self.managers
        leaders = self.leaders
        people_group = PeopleGroupFactory(organization=organization)
        user = self.get_parameterized_test_user(role, instances=[people_group])
        self.client.force_authenticate(user)
        people_group.members.add(*members)
        people_group.managers.add(*managers)
        people_group.leaders.add(*leaders)
        payload = {
            "users": [u.id for u in members + managers + leaders],
        }
        response = self.client.post(
            reverse(
                "PeopleGroup-remove-member",
                args=(organization.code, people_group.pk),
            ),
            payload,
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_204_NO_CONTENT:
            for member in members:
                self.assertNotIn(member, people_group.members.all())
            for manager in managers:
                self.assertNotIn(manager, people_group.managers.all())
            for leader in leaders:
                self.assertNotIn(leader, people_group.leaders.all())


class PeopleGroupFeaturedProjectTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.projects = ProjectFactory.create_batch(3, organizations=[cls.organization])
        cls.retrieved_people_group = PeopleGroupFactory(organization=cls.organization)
        cls.retrieved_featured_projects = {
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
        cls.retrieved_group_projects = {
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
        cls.retrieved_featured_group_project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[cls.organization],
        )
        cls.retrieved_people_group.featured_projects.add(
            cls.retrieved_featured_group_project,
            *list(cls.retrieved_featured_projects.values())
        )
        cls.retrieved_featured_group_project.member_people_groups.add(
            cls.retrieved_people_group
        )
        for project in cls.retrieved_group_projects.values():
            project.member_people_groups.add(cls.retrieved_people_group)

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_ADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_FACILITATOR, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
            (TestRoles.GROUP_LEADER, status.HTTP_204_NO_CONTENT),
            (TestRoles.GROUP_MANAGER, status.HTTP_204_NO_CONTENT),
            (TestRoles.GROUP_MEMBER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_add_featured_project(self, role, expected_code):
        organization = self.organization
        projects = self.projects
        people_group = PeopleGroupFactory(organization=organization)
        user = self.get_parameterized_test_user(role, instances=[people_group])
        self.client.force_authenticate(user)
        payload = {"featured_projects": [p.pk for p in projects]}
        response = self.client.post(
            reverse(
                "PeopleGroup-add-featured-project",
                args=(organization.code, people_group.pk),
            ),
            payload,
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_204_NO_CONTENT:
            for project in projects:
                self.assertIn(project, people_group.featured_projects.all())

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_ADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_FACILITATOR, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
            (TestRoles.GROUP_LEADER, status.HTTP_204_NO_CONTENT),
            (TestRoles.GROUP_MANAGER, status.HTTP_204_NO_CONTENT),
            (TestRoles.GROUP_MEMBER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_remove_featured_project(self, role, expected_code):
        organization = self.organization
        projects = self.projects
        people_group = PeopleGroupFactory(organization=organization)
        user = self.get_parameterized_test_user(role, instances=[people_group])
        self.client.force_authenticate(user)
        people_group.featured_projects.add(*projects)
        payload = {"featured_projects": [p.pk for p in projects]}
        response = self.client.post(
            reverse(
                "PeopleGroup-remove-featured-project",
                args=(organization.code, people_group.pk),
            ),
            payload,
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_204_NO_CONTENT:
            for project in projects:
                self.assertNotIn(project, people_group.featured_projects.all())

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, ("public",)),
            (TestRoles.DEFAULT, ("public",)),
            (TestRoles.SUPERADMIN, ("public", "private", "org")),
            (TestRoles.ORG_ADMIN, ("public", "private", "org")),
            (TestRoles.ORG_FACILITATOR, ("public", "private", "org")),
            (TestRoles.ORG_USER, ("public", "org")),
            (TestRoles.GROUP_LEADER, ("public",)),
            (TestRoles.GROUP_MANAGER, ("public",)),
            (TestRoles.GROUP_MEMBER, ("public",)),
        ]
    )
    def test_retrieve_featured_projects(self, role, retrieved_projects):
        organization = self.organization
        people_group = self.retrieved_people_group
        featured_projects = self.retrieved_featured_projects
        group_projects = self.retrieved_group_projects
        user = self.get_parameterized_test_user(role, instances=[people_group])
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse(
                "PeopleGroup-project",
                args=(organization.code, people_group.pk),
            ),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(content[0]["id"], self.retrieved_featured_group_project.id)
        self.assertEqual(
            {p["id"] for p in content[1 : len(retrieved_projects) + 1]},
            {featured_projects[p].id for p in retrieved_projects},
        )
        self.assertEqual(
            {p["id"] for p in content[len(retrieved_projects) + 1 :]},
            {group_projects[p].id for p in retrieved_projects},
        )
        for project in content:
            if project["id"] == self.retrieved_featured_group_project.id:
                self.assertTrue(project["is_featured"])
                self.assertTrue(project["is_group_project"])
            elif project["id"] in [p.id for p in featured_projects.values()]:
                self.assertTrue(project["is_featured"])
                self.assertFalse(project["is_group_project"])
            elif project["id"] in [p.id for p in group_projects.values()]:
                self.assertFalse(project["is_featured"])
                self.assertTrue(project["is_group_project"])

    @parameterized.expand(
        [
            (TestRoles.PROJECT_OWNER, ("public", "private", "org")),
            (TestRoles.PROJECT_REVIEWER, ("public", "private", "org")),
            (TestRoles.PROJECT_MEMBER, ("public", "private", "org")),
        ]
    )
    def test_retrieve_featured_projects_project_roles(self, role, retrieved_projects):
        organization = self.organization
        people_group = self.retrieved_people_group
        featured_projects = self.retrieved_featured_projects
        group_projects = self.retrieved_group_projects
        instances = [
            self.retrieved_featured_group_project,
            *list(featured_projects.values()),
            *list(group_projects.values()),
        ]
        user = self.get_parameterized_test_user(role, instances=instances)
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse(
                "PeopleGroup-project",
                args=(organization.code, people_group.pk),
            ),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(content[0]["id"], self.retrieved_featured_group_project.id)
        self.assertEqual(
            {p["id"] for p in content[1 : len(retrieved_projects) + 1]},
            {featured_projects[p].id for p in retrieved_projects},
        )
        self.assertEqual(
            {p["id"] for p in content[len(retrieved_projects) + 1 :]},
            {group_projects[p].id for p in retrieved_projects},
        )
        for project in content:
            if project["id"] == self.retrieved_featured_group_project.id:
                self.assertTrue(project["is_featured"])
                self.assertTrue(project["is_group_project"])
            elif project["id"] in [p.id for p in featured_projects.values()]:
                self.assertTrue(project["is_featured"])
                self.assertFalse(project["is_group_project"])
            elif project["id"] in [p.id for p in group_projects.values()]:
                self.assertFalse(project["is_featured"])
                self.assertTrue(project["is_group_project"])


class ValidatePeopleGroupTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.user = UserFactory(groups=[cls.organization.get_admins()])

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=self.user)

    def test_create_parent_in_other_organization(self):
        parent = PeopleGroupFactory()
        payload = {
            "name": faker.name(),
            "description": faker.text(),
            "email": faker.email(),
            "parent": parent.id,
        }
        response = self.client.post(
            reverse("PeopleGroup-list", args=(self.organization.code,)), payload
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertApiValidationError(
            response,
            {"parent": ["The parent group must belong to the same organization"]},
        )

    def test_update_parent_in_other_organization(self):
        people_group = PeopleGroupFactory(organization=self.organization)
        parent = PeopleGroupFactory()
        payload = {
            "parent": parent.id,
        }
        response = self.client.patch(
            reverse(
                "PeopleGroup-detail", args=(self.organization.code, people_group.pk)
            ),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertApiValidationError(
            response,
            {"parent": ["The parent group must belong to the same organization"]},
        )

    def test_update_organization(self):
        people_group = PeopleGroupFactory(organization=self.organization)
        payload = {
            "organization": OrganizationFactory().code,
        }
        response = self.client.patch(
            reverse(
                "PeopleGroup-detail", args=(self.organization.code, people_group.pk)
            ),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertApiValidationError(
            response,
            {"organization": ["The organization of a group cannot be changed"]},
        )

    def test_own_parent(self):
        people_group = PeopleGroupFactory(organization=self.organization)
        payload = {
            "parent": people_group.id,
        }
        response = self.client.patch(
            reverse(
                "PeopleGroup-detail", args=(self.organization.code, people_group.pk)
            ),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertApiValidationError(
            response,
            {"parent": ["You are trying to create a loop in the group's hierarchy"]},
        )

    def test_create_hierarchy_loop(self):
        group_1 = PeopleGroupFactory(organization=self.organization)
        group_2 = PeopleGroupFactory(organization=self.organization, parent=group_1)
        group_3 = PeopleGroupFactory(organization=self.organization, parent=group_2)
        payload = {"parent": group_3.id}
        response = self.client.patch(
            reverse("PeopleGroup-detail", args=(self.organization.code, group_1.pk)),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertApiValidationError(
            response,
            {"parent": ["You are trying to create a loop in the group's hierarchy"]},
        )

    def test_create_other_organization_in_payload(self):
        payload = {
            "name": faker.name(),
            "description": faker.text(),
            "email": faker.email(),
            "organization": OrganizationFactory().code,
        }
        response = self.client.post(
            reverse("PeopleGroup-list", args=(self.organization.code,)), payload
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["organization"], self.organization.code)

    def test_add_featured_project_without_rights(self):
        people_group = PeopleGroupFactory(organization=self.organization)
        project = ProjectFactory(publication_status=Project.PublicationStatus.PRIVATE)

        payload = {"featured_projects": [project.id]}
        response = self.client.post(
            reverse(
                "PeopleGroup-add-featured-project",
                args=(self.organization.code, people_group.pk),
            ),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertApiPermissionError(
            response,
            "You cannot add projects that you do not have access to",
        )

    def test_remove_featured_project_without_rights(self):
        people_group = PeopleGroupFactory(organization=self.organization)
        project = ProjectFactory(publication_status=Project.PublicationStatus.PRIVATE)
        people_group.featured_projects.add(project)

        payload = {"project": project.id}
        response = self.client.post(
            reverse(
                "PeopleGroup-remove-featured-project",
                args=(self.organization.code, people_group.pk),
            ),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_set_root_group_as_parent_with_none(self):
        organization = self.organization
        child = PeopleGroupFactory(organization=organization)
        payload = {"parent": None}
        response = self.client.patch(
            reverse(
                "PeopleGroup-detail",
                args=(organization.code, child.pk),
            ),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        child.refresh_from_db()
        self.assertEqual(
            child.parent,
            PeopleGroup.objects.get(organization=organization, is_root=True),
        )


class MiscPeopleGroupTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()

    def test_annotate_members(self):
        people_group = PeopleGroupFactory(
            publication_status=PeopleGroup.PublicationStatus.PUBLIC,
            organization=self.organization,
        )
        leaders_managers = UserFactory.create_batch(2)
        managers = UserFactory.create_batch(2)
        leaders_members = UserFactory.create_batch(2)
        members = UserFactory.create_batch(2)

        people_group.managers.add(*managers, *leaders_managers)
        people_group.members.add(*members, *leaders_members)
        people_group.leaders.add(*leaders_managers, *leaders_members)

        response = self.client.get(
            reverse(
                "PeopleGroup-member",
                args=(people_group.organization.code, people_group.pk),
            )
        )

        self.assertEqual(response.status_code, 200)
        content = response.json()
        results = content["results"]

        batch_1 = results[:2]
        batch_1_ids = [user["id"] for user in batch_1]
        leaders_managers_ids = [user.id for user in leaders_managers]
        self.assertEqual(leaders_managers_ids.sort(), batch_1_ids.sort())
        self.assertTrue(all(user["is_manager"] is True for user in batch_1))
        self.assertTrue(all(user["is_leader"] is True for user in batch_1))

        batch_2 = results[2:4]
        batch_2_ids = [user["id"] for user in batch_2]
        leaders_members_ids = [user.id for user in leaders_members]
        self.assertEqual(leaders_members_ids.sort(), batch_2_ids.sort())
        self.assertTrue(all(user["is_manager"] is False for user in batch_2))
        self.assertTrue(all(user["is_leader"] is True for user in batch_2))

        batch_3 = results[4:6]
        batch_3_ids = [user["id"] for user in batch_3]
        managers_ids = [user.id for user in managers]
        self.assertEqual(managers_ids.sort(), batch_3_ids.sort())
        self.assertTrue(all(user["is_manager"] is True for user in batch_3))
        self.assertTrue(all(user["is_leader"] is False for user in batch_3))

        batch_4 = results[6:]
        batch_4_ids = [user["id"] for user in batch_4]
        members_ids = [user.id for user in members]
        self.assertEqual(members_ids.sort(), batch_4_ids.sort())
        self.assertTrue(all(user["is_manager"] is False for user in batch_4))
        self.assertTrue(all(user["is_leader"] is False for user in batch_4))

    def test_root_group_creation(self):
        organization = OrganizationFactory()
        root_people_group = PeopleGroup.objects.filter(
            organization=organization, is_root=True
        )
        self.assertTrue(root_people_group.exists())
        self.assertEqual(root_people_group.count(), 1)

    def test_root_group_is_default_parent(self):
        organization = self.organization
        root_people_group = PeopleGroup.update_or_create_root(organization)
        payload = {
            "name": faker.name(),
            "description": faker.text(),
            "email": faker.email(),
        }
        user = UserFactory(groups=[organization.get_admins()])
        self.client.force_authenticate(user)
        response = self.client.post(
            reverse("PeopleGroup-list", args=(organization.code,)),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        people_group = PeopleGroup.objects.get(id=response.json()["id"])
        self.assertEqual(people_group.parent, root_people_group)

    def test_add_member_in_leaders_group(self):
        people_group = PeopleGroupFactory(
            publication_status=PeopleGroup.PublicationStatus.PUBLIC,
            organization=self.organization,
        )
        self.client.force_authenticate(UserFactory(groups=[get_superadmins_group()]))
        user = UserFactory()
        people_group.members.add(user)
        payload = {
            PeopleGroup.DefaultGroup.LEADERS: [user.id],
        }
        response = self.client.post(
            reverse(
                "PeopleGroup-add-member",
                args=(people_group.organization.code, people_group.pk),
            ),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertIn(user, people_group.leaders.all())

    def test_add_leader_in_members_group(self):
        people_group = PeopleGroupFactory(
            publication_status=PeopleGroup.PublicationStatus.PUBLIC,
            organization=self.organization,
        )
        self.client.force_authenticate(UserFactory(groups=[get_superadmins_group()]))
        user = UserFactory()
        people_group.leaders.add(user)
        payload = {
            PeopleGroup.DefaultGroup.MEMBERS: [user.id],
        }
        response = self.client.post(
            reverse(
                "PeopleGroup-add-member",
                args=(people_group.organization.code, people_group.pk),
            ),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertIn(user, people_group.members.all())

    def test_add_member_in_managers_group(self):
        people_group = PeopleGroupFactory(
            publication_status=PeopleGroup.PublicationStatus.PUBLIC,
            organization=self.organization,
        )
        self.client.force_authenticate(UserFactory(groups=[get_superadmins_group()]))
        user = UserFactory()
        people_group.members.add(user)
        payload = {
            PeopleGroup.DefaultGroup.MANAGERS: [user.id],
        }
        response = self.client.post(
            reverse(
                "PeopleGroup-add-member",
                args=(people_group.organization.code, people_group.pk),
            ),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertIn(user, people_group.managers.all())
        self.assertNotIn(user, people_group.members.all())

    def test_get_slug(self):
        name = "My AMazing TeST GroUP !"
        people_group = PeopleGroupFactory(name=name, organization=self.organization)
        self.assertEqual(people_group.slug, "my-amazing-test-group")
        people_group = PeopleGroupFactory(name=name, organization=self.organization)
        self.assertEqual(people_group.slug, "my-amazing-test-group-1")
        people_group = PeopleGroupFactory(name=name, organization=self.organization)
        self.assertEqual(people_group.slug, "my-amazing-test-group-2")
        people_group = PeopleGroupFactory(name="", organization=self.organization)
        self.assertTrue(people_group.slug.startswith("group"), people_group.slug)

    def test_multiple_lookups(self):
        user = UserFactory()
        self.client.force_authenticate(user)
        people_group = PeopleGroupFactory(
            publication_status=PeopleGroup.PublicationStatus.PUBLIC,
            organization=self.organization,
        )
        response = self.client.get(
            reverse(
                "PeopleGroup-detail",
                args=(people_group.organization.code, people_group.pk),
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["slug"], people_group.slug)
        response = self.client.get(
            reverse(
                "PeopleGroup-detail",
                args=(people_group.organization.code, people_group.slug),
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], people_group.id)

    def test_roles_are_deleted_on_group_delete(self):
        people_group = PeopleGroupFactory(organization=self.organization)
        roles_names = [r.name for r in people_group.groups.all()]
        user = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(user)
        response = self.client.delete(
            reverse(
                "PeopleGroup-detail",
                args=(people_group.organization.code, people_group.pk),
            )
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Group.objects.filter(name__in=roles_names).exists())

    def test_parent_update_on_parent_delete(self):
        main_parent = PeopleGroupFactory(organization=self.organization)
        parent = PeopleGroupFactory(organization=self.organization, parent=main_parent)
        child = PeopleGroupFactory(organization=self.organization, parent=parent)
        user = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(user)
        response = self.client.delete(
            reverse(
                "PeopleGroup-detail",
                args=(parent.organization.code, parent.pk),
            )
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        child.refresh_from_db()
        self.assertEqual(child.parent, main_parent)
