from unittest.mock import patch

from django.contrib.auth.models import Group
from django.urls import reverse
from faker import Faker
from parameterized import parameterized
from rest_framework import status

from apps.accounts.factories import PeopleGroupFactory, SeedUserFactory, UserFactory
from apps.accounts.models import PeopleGroup
from apps.accounts.utils import get_superadmins_group
from apps.commons.models import GroupData
from apps.commons.test import JwtAPITestCase, TestRoles
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory
from apps.projects.models import Project

faker = Faker()


class ReadPeopleGroupTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.groups = {
            "public": PeopleGroupFactory(
                publication_status=PeopleGroup.PublicationStatus.PUBLIC,
                organization=cls.organization,
            ),
            "private": PeopleGroupFactory(
                publication_status=PeopleGroup.PublicationStatus.PRIVATE,
                organization=cls.organization,
            ),
            "org": PeopleGroupFactory(
                publication_status=PeopleGroup.PublicationStatus.ORG,
                organization=cls.organization,
            ),
            "member": PeopleGroupFactory(
                publication_status=PeopleGroup.PublicationStatus.PRIVATE,
                organization=cls.organization,
            ),
            "root": PeopleGroup.update_or_create_root(cls.organization),
        }

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, ("public",)),
            (TestRoles.DEFAULT, ("public",)),
            (TestRoles.SUPERADMIN, ("public", "private", "org", "member")),
            (TestRoles.ORG_ADMIN, ("public", "private", "org", "member")),
            (TestRoles.ORG_FACILITATOR, ("public", "private", "org", "member")),
            (TestRoles.ORG_USER, ("public", "org")),
            (TestRoles.GROUP_LEADER, ("public", "member")),
            (TestRoles.GROUP_MANAGER, ("public", "member")),
            (TestRoles.GROUP_MEMBER, ("public", "member")),
        ]
    )
    def test_retrieve_people_groups(self, role, expected_groups):
        organization = self.organization
        member_group = self.groups["member"]
        user = self.get_parameterized_test_user(role, instances=[member_group])
        self.client.force_authenticate(user)
        for people_group_type, people_group in self.groups.items():
            response = self.client.get(
                reverse(
                    "PeopleGroup-detail",
                    args=(
                        organization.code,
                        people_group.id,
                    ),
                )
            )
            member_response = self.client.get(
                reverse(
                    "PeopleGroup-member",
                    args=(
                        organization.code,
                        people_group.id,
                    ),
                )
            )
            project_response = self.client.get(
                reverse(
                    "PeopleGroup-project",
                    args=(
                        organization.code,
                        people_group.id,
                    ),
                )
            )
            if people_group_type in expected_groups:
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(member_response.status_code, status.HTTP_200_OK)
                self.assertEqual(project_response.status_code, status.HTTP_200_OK)
            else:
                self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
                self.assertEqual(member_response.status_code, status.HTTP_404_NOT_FOUND)
                self.assertEqual(
                    project_response.status_code, status.HTTP_404_NOT_FOUND
                )

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, ("public",)),
            (TestRoles.DEFAULT, ("public",)),
            (TestRoles.SUPERADMIN, ("public", "private", "org", "member")),
            (TestRoles.ORG_ADMIN, ("public", "private", "org", "member")),
            (TestRoles.ORG_FACILITATOR, ("public", "private", "org", "member")),
            (TestRoles.ORG_USER, ("public", "org")),
            (TestRoles.GROUP_LEADER, ("public", "member")),
            (TestRoles.GROUP_MANAGER, ("public", "member")),
            (TestRoles.GROUP_MEMBER, ("public", "member")),
        ]
    )
    def test_list_people_groups(self, role, expected_groups):
        organization = self.organization
        member_group = self.groups["member"]
        user = self.get_parameterized_test_user(role, instances=[member_group])
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("PeopleGroup-list", args=(organization.code,))
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), len(expected_groups))
        self.assertEqual(
            {people_group["id"] for people_group in content},
            {
                self.groups[people_group_type].id
                for people_group_type in expected_groups
            },
        )


class ReadPeopleGroupHierarchyTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.root_group = PeopleGroup.update_or_create_root(cls.organization)
        cls.level_1 = PeopleGroupFactory(
            publication_status=PeopleGroup.PublicationStatus.PUBLIC,
            organization=cls.organization,
            parent=cls.root_group,
        )
        cls.level_2 = PeopleGroupFactory(
            publication_status=PeopleGroup.PublicationStatus.PRIVATE,
            organization=cls.organization,
            parent=cls.level_1,
        )
        cls.level_3 = PeopleGroupFactory(
            publication_status=PeopleGroup.PublicationStatus.ORG,
            organization=cls.organization,
            parent=cls.level_2,
        )
        cls.group = PeopleGroupFactory(
            publication_status=PeopleGroup.PublicationStatus.PUBLIC,
            organization=cls.organization,
            parent=cls.level_3,
        )
        cls.public_child = PeopleGroupFactory(
            publication_status=PeopleGroup.PublicationStatus.PUBLIC,
            organization=cls.organization,
            parent=cls.group,
        )
        cls.private_child = PeopleGroupFactory(
            publication_status=PeopleGroup.PublicationStatus.PRIVATE,
            organization=cls.organization,
            parent=cls.group,
        )
        cls.org_child = PeopleGroupFactory(
            publication_status=PeopleGroup.PublicationStatus.ORG,
            organization=cls.organization,
            parent=cls.group,
        )
        cls.parents = {
            "level_1": cls.level_1,
            "level_2": cls.level_2,
            "level_3": cls.level_3,
        }
        cls.children = {
            "public": cls.public_child,
            "private": cls.private_child,
            "org": cls.org_child,
        }

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, ["level_1"], ("public",)),
            (TestRoles.DEFAULT, ["level_1"], ("public",)),
            (
                TestRoles.SUPERADMIN,
                ["level_1", "level_2", "level_3"],
                ("public", "private", "org"),
            ),
            (
                TestRoles.ORG_ADMIN,
                ["level_1", "level_2", "level_3"],
                ("public", "private", "org"),
            ),
            (
                TestRoles.ORG_FACILITATOR,
                ["level_1", "level_2", "level_3"],
                ("public", "private", "org"),
            ),
            (TestRoles.ORG_USER, ["level_1", "level_3"], ("public", "org")),
            (TestRoles.GROUP_LEADER, ["level_1", "level_2"], ("public", "private")),
            (TestRoles.GROUP_MANAGER, ["level_1", "level_2"], ("public", "private")),
            (TestRoles.GROUP_MEMBER, ["level_1", "level_2"], ("public", "private")),
        ]
    )
    def test_retrieve_people_group_hierarchy(
        self, role, expected_parents, expected_children
    ):
        user = self.get_parameterized_test_user(
            role, instances=[self.level_2, self.private_child]
        )
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse(
                "PeopleGroup-detail",
                args=(self.organization.code, self.group.id),
            ),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()

        hierarchy = content["hierarchy"]
        self.assertEqual(len(hierarchy), len(expected_parents))
        for i, parent in enumerate(expected_parents):
            self.assertEqual(hierarchy[i]["id"], self.parents[parent].id)
            self.assertEqual(hierarchy[i]["order"], i)

        children = content["children"]
        self.assertEqual(len(children), len(expected_children))
        self.assertSetEqual(
            {child["id"] for child in children},
            {self.children[child].id for child in expected_children},
        )


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
            *list(cls.retrieved_featured_projects.values()),
        )
        cls.retrieved_featured_group_project.member_groups.add(
            cls.retrieved_people_group
        )
        for project in cls.retrieved_group_projects.values():
            project.member_groups.add(cls.retrieved_people_group)

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


class PeopleGroupProjectRolesTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.project = ProjectFactory(organizations=[cls.organization])
        cls.superadmin = UserFactory(groups=[get_superadmins_group()])
        cls.user_1 = UserFactory()
        cls.user_2 = UserFactory()
        cls.user_3 = UserFactory()

    @parameterized.expand(
        [
            (GroupData.Role.MEMBER_GROUPS,),
            (GroupData.Role.OWNER_GROUPS,),
            (GroupData.Role.REVIEWER_GROUPS,),
        ]
    )
    def test_assign_role_on_project_group_member_changer(self, project_role):
        self.client.force_authenticate(user=self.superadmin)
        people_group = PeopleGroupFactory(organization=self.organization)
        people_group.members.add(self.user_1)
        people_group.managers.add(self.user_2)
        people_group.leaders.add(self.user_3)
        payload = {
            project_role: [people_group.id],
        }
        response = self.client.post(
            reverse("Project-add-member", args=(self.project.id,)),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.project.refresh_from_db()
        for user in [self.user_1, self.user_2, self.user_3]:
            self.assertIn(user, getattr(self.project, f"{project_role}_users").all())
        payload = {
            "people_groups": [people_group.id],
        }
        response = self.client.post(
            reverse("Project-remove-member", args=(self.project.id,)),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.project.refresh_from_db()
        for user in [self.user_1, self.user_2, self.user_3]:
            self.assertNotIn(user, getattr(self.project, f"{project_role}_users").all())

    @parameterized.expand(
        [
            (GroupData.Role.MEMBER_GROUPS,),
            (GroupData.Role.OWNER_GROUPS,),
            (GroupData.Role.REVIEWER_GROUPS,),
        ]
    )
    def test_assign_role_on_group_member_changer(self, project_role):
        self.client.force_authenticate(user=self.superadmin)
        people_group = PeopleGroupFactory(organization=self.organization)
        getattr(self.project, f"get_{project_role}")().people_groups.add(people_group)
        payload = {
            GroupData.Role.LEADERS: [self.user_1.id],
            GroupData.Role.MANAGERS: [self.user_2.id],
            GroupData.Role.MEMBERS: [self.user_3.id],
        }
        response = self.client.post(
            reverse(
                "PeopleGroup-add-member", args=(self.organization.code, people_group.id)
            ),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.project.refresh_from_db()
        for user in [self.user_1, self.user_2, self.user_3]:
            self.assertIn(user, getattr(self.project, f"{project_role}_users").all())
        payload = {
            "users": [self.user_1.id, self.user_2.id, self.user_3.id],
        }
        response = self.client.post(
            reverse(
                "PeopleGroup-remove-member",
                args=(self.organization.code, people_group.id),
            ),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.project.refresh_from_db()
        for user in [self.user_1, self.user_2, self.user_3]:
            self.assertNotIn(user, getattr(self.project, f"{project_role}_users").all())

    @parameterized.expand(
        [
            (GroupData.Role.MEMBER_GROUPS,),
            (GroupData.Role.OWNER_GROUPS,),
            (GroupData.Role.REVIEWER_GROUPS,),
        ]
    )
    def test_assign_role_on_user_roles_update(self, project_role):
        self.client.force_authenticate(user=self.superadmin)
        people_group = PeopleGroupFactory(organization=self.organization)
        user = SeedUserFactory()
        for group in [
            people_group.get_members(),
            people_group.get_managers(),
            people_group.get_leaders(),
        ]:
            getattr(self.project, f"get_{project_role}")().people_groups.add(
                people_group
            )
            payload = {
                "roles_to_add": [group.name],
            }
            response = self.client.patch(
                reverse("ProjectUser-detail", args=(user.id,)),
                payload,
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.project.refresh_from_db()
            self.assertIn(user, getattr(self.project, f"{project_role}_users").all())
            payload = {
                "roles_to_remove": [group.name],
            }
            response = self.client.patch(
                reverse("ProjectUser-detail", args=(user.id,)),
                payload,
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.project.refresh_from_db()
            self.assertNotIn(user, getattr(self.project, f"{project_role}_users").all())

    @parameterized.expand(
        [
            (GroupData.Role.MEMBER_GROUPS,),
            (GroupData.Role.OWNER_GROUPS,),
            (GroupData.Role.REVIEWER_GROUPS,),
        ]
    )
    @patch("services.keycloak.interface.KeycloakService.send_email")
    def test_assign_role_on_user_create(self, project_role, mocked):
        mocked.return_value = {}
        self.client.force_authenticate(user=self.superadmin)
        people_group = PeopleGroupFactory(organization=self.organization)
        for group in [
            people_group.get_members(),
            people_group.get_managers(),
            people_group.get_leaders(),
        ]:
            getattr(self.project, f"get_{project_role}")().people_groups.add(
                people_group
            )
            payload = {
                "email": f"{faker.uuid4()}@{faker.domain_name()}",
                "given_name": faker.first_name(),
                "family_name": faker.last_name(),
                "roles_to_add": [self.organization.get_users().name, group.name],
            }
            response = self.client.post(
                reverse("ProjectUser-list"),
                payload,
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            content = response.json()
            self.project.refresh_from_db()
            self.assertIn(
                content["id"],
                getattr(self.project, f"{project_role}_users").values_list(
                    "id", flat=True
                ),
            )


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
        cls.superadmin = UserFactory(groups=[get_superadmins_group()])

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
        self.client.force_authenticate(self.superadmin)
        organization = self.organization
        root_people_group = PeopleGroup.update_or_create_root(organization)
        payload = {
            "name": faker.name(),
            "description": faker.text(),
            "email": faker.email(),
        }
        response = self.client.post(
            reverse("PeopleGroup-list", args=(organization.code,)),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        people_group = PeopleGroup.objects.get(id=response.json()["id"])
        self.assertEqual(people_group.parent, root_people_group)

    def test_add_member_in_leaders_group(self):
        self.client.force_authenticate(self.superadmin)
        people_group = PeopleGroupFactory(
            publication_status=PeopleGroup.PublicationStatus.PUBLIC,
            organization=self.organization,
        )
        user = UserFactory()
        people_group.members.add(user)
        payload = {
            GroupData.Role.LEADERS: [user.id],
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
        self.client.force_authenticate(self.superadmin)
        people_group = PeopleGroupFactory(
            publication_status=PeopleGroup.PublicationStatus.PUBLIC,
            organization=self.organization,
        )
        user = UserFactory()
        people_group.leaders.add(user)
        payload = {
            GroupData.Role.MEMBERS: [user.id],
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
        self.client.force_authenticate(self.superadmin)
        people_group = PeopleGroupFactory(
            publication_status=PeopleGroup.PublicationStatus.PUBLIC,
            organization=self.organization,
        )
        user = UserFactory()
        people_group.members.add(user)
        payload = {
            GroupData.Role.MANAGERS: [user.id],
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

    def test_outdated_slug(self):
        self.client.force_authenticate(self.superadmin)

        name_a = "name-a"
        name_b = "name-b"
        name_c = "name-c"
        parent = PeopleGroupFactory(organization=self.organization)
        people_group = PeopleGroupFactory(
            name=name_a, organization=self.organization, parent=parent
        )

        # Check that the slug is updated and the old one is stored in outdated_slugs
        payload = {"name": name_b}
        response = self.client.patch(
            reverse(
                "PeopleGroup-detail", args=(self.organization.code, people_group.id)
            ),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        people_group.refresh_from_db()
        self.assertEqual(people_group.slug, "name-b")
        self.assertSetEqual({"name-a"}, set(people_group.outdated_slugs))

        # Check that multiple_slug is correctly updated
        payload = {"name": name_c}
        response = self.client.patch(
            reverse(
                "PeopleGroup-detail", args=(self.organization.code, people_group.id)
            ),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        people_group.refresh_from_db()
        self.assertEqual(people_group.slug, "name-c")
        self.assertSetEqual({"name-a", "name-b"}, set(people_group.outdated_slugs))

        # Check that outdated_slugs are reused if relevant
        payload = {"name": name_b}
        response = self.client.patch(
            reverse(
                "PeopleGroup-detail", args=(self.organization.code, people_group.id)
            ),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        people_group.refresh_from_db()
        self.assertEqual(people_group.slug, "name-b")
        self.assertSetEqual(
            {"name-a", "name-b", "name-c"}, set(people_group.outdated_slugs)
        )

        # Check that outdated_slugs respect unicity
        payload = {"name": name_a}
        response = self.client.post(
            reverse("PeopleGroup-list", args=(self.organization.code,)), payload
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        content = response.json()
        self.assertEqual(content["slug"], "name-a-1")

    def test_roles_are_deleted_on_group_delete(self):
        self.client.force_authenticate(self.superadmin)
        people_group = PeopleGroupFactory(organization=self.organization)
        roles_names = [r.name for r in people_group.groups.all()]
        response = self.client.delete(
            reverse(
                "PeopleGroup-detail",
                args=(people_group.organization.code, people_group.pk),
            )
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Group.objects.filter(name__in=roles_names).exists())

    def test_parent_update_on_parent_delete(self):
        self.client.force_authenticate(self.superadmin)
        main_parent = PeopleGroupFactory(organization=self.organization)
        parent = PeopleGroupFactory(organization=self.organization, parent=main_parent)
        child = PeopleGroupFactory(organization=self.organization, parent=parent)
        response = self.client.delete(
            reverse(
                "PeopleGroup-detail",
                args=(parent.organization.code, parent.pk),
            )
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        child.refresh_from_db()
        self.assertEqual(child.parent, main_parent)
