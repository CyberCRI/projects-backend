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
                "members": [m.keycloak_id for m in members],
                "managers": [r.keycloak_id for r in managers],
                "leaders": [r.keycloak_id for r in leaders],
            },
            "featured_projects": [p.pk for p in projects],
        }
        response = self.client.post(
            reverse("PeopleGroup-list", args=(organization.code,)),
            payload,
        )
        assert response.status_code == expected_code
        if expected_code == status.HTTP_201_CREATED:
            assert response.status_code == 201
            assert response.data["name"] == payload["name"]
            assert response.data["description"] == payload["description"]
            assert response.data["email"] == payload["email"]
            assert response.data["organization"] == organization.code
            assert response.data["hierarchy"][0]["id"] == parent.id
            assert response.data["hierarchy"][0]["slug"] == parent.slug
            people_group = PeopleGroup.objects.get(id=response.json()["id"])
            assert all(member in people_group.members.all() for member in members)
            assert all(manager in people_group.managers.all() for manager in managers)
            assert all(leader in people_group.leaders.all() for leader in leaders)
            assert all(
                project in people_group.featured_projects.all() for project in projects
            )


class UpdatePeopleGroupTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()

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
        organization = self.organization
        people_group = PeopleGroupFactory(organization=organization)
        people_group.description = faker.text()
        people_group.save()
        user = self.get_parameterized_test_user(role, instances=[people_group])
        self.client.force_authenticate(user)
        payload = {
            "description": faker.text(),
        }
        response = self.client.patch(
            reverse(
                "PeopleGroup-detail",
                args=(organization.code, people_group.pk),
            ),
            payload,
        )
        assert response.status_code == expected_code
        if expected_code == status.HTTP_200_OK:
            assert response.json()["description"] == payload["description"]


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
        assert response.status_code == expected_code
        if expected_code == status.HTTP_204_NO_CONTENT:
            assert not PeopleGroup.objects.filter(id=people_group.id).exists()


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
            "members": [m.keycloak_id for m in members],
            "managers": [r.keycloak_id for r in managers],
            "leaders": [r.keycloak_id for r in leaders],
        }
        response = self.client.post(
            reverse(
                "PeopleGroup-add-member",
                args=(organization.code, people_group.pk),
            ),
            payload,
        )
        assert response.status_code == expected_code
        if expected_code == status.HTTP_204_NO_CONTENT:
            assert all(member in people_group.members.all() for member in members)
            assert all(manager in people_group.managers.all() for manager in managers)
            assert all(leader in people_group.leaders.all() for leader in leaders)

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
            "users": [u.keycloak_id for u in members + managers + leaders],
        }
        response = self.client.post(
            reverse(
                "PeopleGroup-remove-member",
                args=(organization.code, people_group.pk),
            ),
            payload,
        )
        assert response.status_code == expected_code
        if expected_code == status.HTTP_204_NO_CONTENT:
            assert all(member not in people_group.members.all() for member in members)
            assert all(
                manager not in people_group.managers.all() for manager in managers
            )
            assert all(leader not in people_group.leaders.all() for leader in leaders)


class PeopleGroupFeaturedProjectTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.projects = ProjectFactory.create_batch(3, organizations=[cls.organization])

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
        assert response.status_code == expected_code
        if expected_code == status.HTTP_204_NO_CONTENT:
            assert all(
                project in people_group.featured_projects.all() for project in projects
            )

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
        assert response.status_code == expected_code
        if expected_code == status.HTTP_204_NO_CONTENT:
            assert all(
                project not in people_group.featured_projects.all()
                for project in projects
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
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["parent"][0],
            "The parent group must belong to the same organization",
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
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["parent"][0],
            "The parent group must belong to the same organization",
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
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["organization"][0],
            "The organization of a group cannot be changed",
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
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["parent"][0],
            "You are trying to create a loop in the group's hierarchy",
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
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json()["parent"][0],
            "You are trying to create a loop in the group's hierarchy",
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
        self.assertEqual(response.status_code, 201)
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
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data["featured_projects"][0],
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
        self.assertEqual(response.status_code, 204)

    def test_give_root_group_a_parent(self):
        organization = self.organization
        root_people_group = PeopleGroup.objects.get(
            organization=organization, is_root=True
        )
        parent = PeopleGroupFactory(organization=organization)
        payload = {"parent": parent.id}
        response = self.client.patch(
            reverse(
                "PeopleGroup-detail",
                args=(organization.code, root_people_group.pk),
            ),
            payload,
        )
        assert response.status_code == 400
        assert response.data["parent"][0] == "The root group cannot have a parent group"

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
        assert response.status_code == 200
        child.refresh_from_db()
        assert child.parent == PeopleGroup.objects.get(
            organization=organization, is_root=True
        )

    def test_update_root_group_with_none_parent(self):
        organization = self.organization
        root = PeopleGroup.objects.get(organization=organization, is_root=True)
        payload = {"parent": None}
        response = self.client.patch(
            reverse(
                "PeopleGroup-detail",
                args=(organization.code, root.pk),
            ),
            payload,
        )
        assert response.status_code == 200


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
        batch_1_ids = [user["keycloak_id"] for user in batch_1]
        leaders_managers_ids = [user.keycloak_id for user in leaders_managers]
        assert leaders_managers_ids.sort() == batch_1_ids.sort()
        assert all(user["is_manager"] is True for user in batch_1)
        assert all(user["is_leader"] is True for user in batch_1)

        batch_2 = results[2:4]
        batch_2_ids = [user["keycloak_id"] for user in batch_2]
        leaders_members_ids = [user.keycloak_id for user in leaders_members]
        assert leaders_members_ids.sort() == batch_2_ids.sort()
        assert all(user["is_manager"] is False for user in batch_2)
        assert all(user["is_leader"] is True for user in batch_2)

        batch_3 = results[4:6]
        batch_3_ids = [user["keycloak_id"] for user in batch_3]
        managers_ids = [user.keycloak_id for user in managers]
        assert managers_ids.sort() == batch_3_ids.sort()
        assert all(user["is_manager"] is True for user in batch_3)
        assert all(user["is_leader"] is False for user in batch_3)

        batch_4 = results[6:]
        batch_4_ids = [user["keycloak_id"] for user in batch_4]
        members_ids = [user.keycloak_id for user in members]
        assert members_ids.sort() == batch_4_ids.sort()
        assert all(user["is_manager"] is False for user in batch_4)
        assert all(user["is_leader"] is False for user in batch_4)

    def test_annotate_projects(self):
        people_group = PeopleGroupFactory(
            publication_status=PeopleGroup.PublicationStatus.PUBLIC,
            organization=self.organization,
        )
        member = UserFactory()
        people_group.members.add(member)

        members_public_projects = ProjectFactory.create_batch(
            2, organizations=[self.organization]
        )
        members_private_projects = ProjectFactory.create_batch(
            2,
            publication_status=Project.PublicationStatus.PRIVATE,
            organizations=[self.organization],
        )
        members_featured_public_projects = ProjectFactory.create_batch(
            2, organizations=[self.organization]
        )

        featured_public_projects = ProjectFactory.create_batch(
            2, organizations=[self.organization]
        )
        featured_private_projects = ProjectFactory.create_batch(
            2,
            publication_status=Project.PublicationStatus.PRIVATE,
            organizations=[self.organization],
        )

        member_projects = (
            members_public_projects
            + members_private_projects
            + members_featured_public_projects
        )
        featured_projects = (
            featured_public_projects
            + featured_private_projects
            + members_featured_public_projects
        )

        for project in member_projects:
            project.members.add(member)

        people_group.featured_projects.add(*(featured_projects))

        response = self.client.get(
            reverse(
                "PeopleGroup-project",
                args=(people_group.organization.code, people_group.pk),
            )
        )
        self.assertEqual(response.status_code, 200)
        content = response.json()

        results = content["results"]
        assert len(results) == 6

        nine_first = results[:4]
        featured_projects_ids = [project.id for project in featured_projects]
        nine_first_ids = [project["id"] for project in nine_first]
        assert featured_projects_ids.sort() == nine_first_ids.sort()
        nine_first_projects = [project["is_featured"] is True for project in nine_first]
        assert all(nine_first_projects) is True

        nine_last = results[-2:]
        member_projects_ids = [project.id for project in member_projects]
        nine_last_ids = [project["id"] for project in nine_last]
        assert member_projects_ids.sort() == nine_last_ids.sort()
        nine_last_projects = [project["is_featured"] is True for project in nine_last]
        assert all(nine_last_projects) is False

    def test_root_group_creation(self):
        organization = OrganizationFactory()
        root_people_group = PeopleGroup.objects.filter(
            organization=organization, is_root=True
        )
        assert root_people_group.exists()
        assert root_people_group.count() == 1

    def test_root_group_is_default_parent(self):
        organization = self.organization
        root_people_group = organization.get_or_create_root_people_group()
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
        assert response.status_code == 201
        people_group = PeopleGroup.objects.get(id=response.json()["id"])
        assert people_group.parent == root_people_group

    def test_add_member_in_leaders_group(self):
        people_group = PeopleGroupFactory(
            publication_status=PeopleGroup.PublicationStatus.PUBLIC,
            organization=self.organization,
        )
        self.client.force_authenticate(UserFactory(groups=[get_superadmins_group()]))
        user = UserFactory()
        people_group.members.add(user)
        payload = {
            PeopleGroup.DefaultGroup.LEADERS: [user.keycloak_id],
        }
        response = self.client.post(
            reverse(
                "PeopleGroup-add-member",
                args=(people_group.organization.code, people_group.pk),
            ),
            payload,
        )
        self.assertEqual(response.status_code, 204)
        assert user in people_group.leaders.all()

    def test_add_leader_in_members_group(self):
        people_group = PeopleGroupFactory(
            publication_status=PeopleGroup.PublicationStatus.PUBLIC,
            organization=self.organization,
        )
        self.client.force_authenticate(UserFactory(groups=[get_superadmins_group()]))
        user = UserFactory()
        people_group.leaders.add(user)
        payload = {
            PeopleGroup.DefaultGroup.MEMBERS: [user.keycloak_id],
        }
        response = self.client.post(
            reverse(
                "PeopleGroup-add-member",
                args=(people_group.organization.code, people_group.pk),
            ),
            payload,
        )
        self.assertEqual(response.status_code, 204)
        assert user in people_group.members.all()

    def test_add_member_in_managers_group(self):
        people_group = PeopleGroupFactory(
            publication_status=PeopleGroup.PublicationStatus.PUBLIC,
            organization=self.organization,
        )
        self.client.force_authenticate(UserFactory(groups=[get_superadmins_group()]))
        user = UserFactory()
        people_group.members.add(user)
        payload = {
            PeopleGroup.DefaultGroup.MANAGERS: [user.keycloak_id],
        }
        response = self.client.post(
            reverse(
                "PeopleGroup-add-member",
                args=(people_group.organization.code, people_group.pk),
            ),
            payload,
        )
        self.assertEqual(response.status_code, 204)
        assert user in people_group.managers.all()
        assert user not in people_group.members.all()

    def test_get_slug(self):
        name = "My AMazing TeST GroUP !"
        people_group = PeopleGroupFactory(name=name, organization=self.organization)
        assert people_group.slug == "my-amazing-test-group"
        people_group = PeopleGroupFactory(name=name, organization=self.organization)
        assert people_group.slug == "my-amazing-test-group-1"
        people_group = PeopleGroupFactory(name=name, organization=self.organization)
        assert people_group.slug == "my-amazing-test-group-2"
        people_group = PeopleGroupFactory(
            name="", type="group", organization=self.organization
        )
        assert people_group.slug.startswith("group")
        people_group = PeopleGroupFactory(
            name="", type="club", organization=self.organization
        )
        assert people_group.slug.startswith("club")

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
        assert response.status_code == 200
        assert response.data["slug"] == people_group.slug
        response = self.client.get(
            reverse(
                "PeopleGroup-detail",
                args=(people_group.organization.code, people_group.slug),
            )
        )
        assert response.status_code == 200
        assert response.data["id"] == people_group.id

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
        assert response.status_code == 204
        assert not Group.objects.filter(name__in=roles_names).exists()
