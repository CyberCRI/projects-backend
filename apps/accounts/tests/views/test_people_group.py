from django.urls import reverse
from faker import Faker

from apps.accounts.factories import PeopleGroupFactory, UserFactory
from apps.accounts.models import PeopleGroup
from apps.commons.test import JwtAPITestCase
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory
from apps.projects.models import Project

faker = Faker()


class PeopleGroupAnonymousTestCase(JwtAPITestCase):
    def test_create_people_group(self):
        organization = OrganizationFactory()
        parent = PeopleGroupFactory(organization=organization)
        payload = {
            "name": faker.name(),
            "description": faker.text(),
            "email": faker.email(),
            "parent": parent.id,
        }
        response = self.client.post(
            reverse("PeopleGroup-list", args=(organization.code,)), payload
        )
        self.assertEqual(response.status_code, 401)

    def test_list_people_group(self):
        organization = OrganizationFactory()
        groups = PeopleGroupFactory.create_batch(
            3,
            organization=organization,
            publication_status=PeopleGroup.PublicationStatus.PUBLIC,
        )
        response = self.client.get(
            f"{reverse('PeopleGroup-list', args=(organization.code,))}?is_root=false"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 3)
        self.assertEqual(
            {item["id"] for item in response.json()["results"]},
            {item.id for item in groups},
        )

    def test_retrieve_people_group(self):
        organization = OrganizationFactory()
        people_group = PeopleGroupFactory(
            organization=organization,
            publication_status=PeopleGroup.PublicationStatus.PUBLIC,
        )
        response = self.client.get(
            reverse("PeopleGroup-detail", args=(organization.code, people_group.pk))
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], people_group.name)

    def test_partial_update_people_group(self):
        people_group = PeopleGroupFactory()
        payload = {
            "description": "update",
        }
        response = self.client.patch(
            reverse(
                "PeopleGroup-detail",
                args=(people_group.organization.code, people_group.pk),
            ),
            payload,
        )
        self.assertEqual(response.status_code, 401)

    def test_destroy_people_group(self):
        people_group = PeopleGroupFactory()
        response = self.client.delete(
            reverse(
                "PeopleGroup-detail",
                args=(people_group.organization.code, people_group.pk),
            )
        )
        self.assertEqual(response.status_code, 401)

    def test_members(self):
        people_group = PeopleGroupFactory()
        payload = {
            PeopleGroup.DefaultGroup.MEMBERS: UserFactory().keycloak_id,
        }
        response = self.client.post(
            reverse(
                "PeopleGroup-add-member",
                args=(people_group.organization.code, people_group.pk),
            ),
            payload,
        )
        self.assertEqual(response.status_code, 401)

    def test_add_members(self):
        people_group = PeopleGroupFactory()
        payload = {
            PeopleGroup.DefaultGroup.MEMBERS: [UserFactory().keycloak_id],
        }
        response = self.client.post(
            reverse(
                "PeopleGroup-add-member",
                args=(people_group.organization.code, people_group.pk),
            ),
            payload,
        )
        self.assertEqual(response.status_code, 401)

    def test_remove_members(self):
        people_group = PeopleGroupFactory()
        user = UserFactory()
        people_group.members.add(user)
        payload = {
            "users": [user.keycloak_id],
        }
        response = self.client.post(
            reverse(
                "PeopleGroup-remove-member",
                args=(people_group.organization.code, people_group.pk),
            ),
            payload,
        )
        self.assertEqual(response.status_code, 401)

    def test_add_featured_project(self):
        people_group = PeopleGroupFactory()
        project = ProjectFactory()

        payload = {
            "featured_projects": [project.id],
        }
        response = self.client.post(
            reverse(
                "PeopleGroup-add-featured-project",
                args=(people_group.organization.code, people_group.pk),
            ),
            payload,
        )
        self.assertEqual(response.status_code, 401)

    def test_remove_featured_project(self):
        people_group = PeopleGroupFactory()
        project = ProjectFactory()
        people_group.featured_projects.add(project)

        payload = {
            "project": project.id,
        }
        response = self.client.post(
            reverse(
                "PeopleGroup-remove-featured-project",
                args=(people_group.organization.code, people_group.pk),
            ),
            payload,
        )
        self.assertEqual(response.status_code, 401)


class PeopleGroupNoPermissionTestCase(JwtAPITestCase):
    def setUp(self):
        super().setUp()
        self.organization = OrganizationFactory()
        self.user = UserFactory()
        self.client.force_authenticate(user=self.user)

    def test_create_people_group(self):
        parent = PeopleGroupFactory(organization=self.organization)
        payload = {
            "name": faker.name(),
            "description": faker.text(),
            "email": faker.email(),
            "parent": parent.id,
        }
        response = self.client.post(
            reverse("PeopleGroup-list", args=(self.organization.code,)), payload
        )
        self.assertEqual(response.status_code, 403)

    def test_list_people_group(self):
        groups = PeopleGroupFactory.create_batch(
            3,
            organization=self.organization,
            publication_status=PeopleGroup.PublicationStatus.PUBLIC,
        )
        response = self.client.get(
            f"{reverse('PeopleGroup-list', args=(self.organization.code,))}?is_root=false"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 3)
        self.assertEqual(
            {item["id"] for item in response.json()["results"]},
            {item.id for item in groups},
        )

    def test_retrieve_people_group(self):
        people_group = PeopleGroupFactory(
            organization=self.organization,
            publication_status=PeopleGroup.PublicationStatus.PUBLIC,
        )
        response = self.client.get(
            reverse(
                "PeopleGroup-detail", args=(self.organization.code, people_group.pk)
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], people_group.name)

    def test_partial_update_people_group(self):
        people_group = PeopleGroupFactory(organization=self.organization)
        payload = {
            "description": "update",
        }
        response = self.client.patch(
            reverse(
                "PeopleGroup-detail", args=(self.organization.code, people_group.pk)
            ),
            payload,
        )
        self.assertEqual(response.status_code, 403)

    def test_destroy_people_group(self):
        people_group = PeopleGroupFactory(organization=self.organization)
        response = self.client.delete(
            reverse(
                "PeopleGroup-detail", args=(self.organization.code, people_group.pk)
            )
        )
        self.assertEqual(response.status_code, 403)

    def test_add_members(self):
        people_group = PeopleGroupFactory(organization=self.organization)
        payload = {
            PeopleGroup.DefaultGroup.MEMBERS: [UserFactory().keycloak_id],
        }
        response = self.client.post(
            reverse(
                "PeopleGroup-add-member",
                args=(self.organization.code, people_group.pk),
            ),
            payload,
        )
        self.assertEqual(response.status_code, 403)

    def test_remove_members(self):
        people_group = PeopleGroupFactory(organization=self.organization)
        user = UserFactory()
        people_group.members.add(user)
        payload = {
            "users": [user.keycloak_id],
        }
        response = self.client.post(
            reverse(
                "PeopleGroup-remove-member",
                args=(self.organization.code, people_group.pk),
            ),
            payload,
        )
        self.assertEqual(response.status_code, 403)

    def test_add_featured_project(self):
        project = ProjectFactory()
        project.members.add(self.user)
        people_group = PeopleGroupFactory(organization=self.organization)

        payload = {
            "featured_projects": [project.id],
        }
        response = self.client.post(
            reverse(
                "PeopleGroup-add-featured-project",
                args=(self.organization.code, people_group.pk),
            ),
            payload,
        )
        self.assertEqual(response.status_code, 403)

    def test_remove_featured_project(self):
        project = ProjectFactory()
        people_group = PeopleGroupFactory(organization=self.organization)
        people_group.featured_projects.add(project)
        project.members.add(self.user)

        payload = {
            "project": project.id,
        }
        response = self.client.post(
            reverse(
                "PeopleGroup-remove-featured-project",
                args=(self.organization.code, people_group.pk),
            ),
            payload,
        )
        self.assertEqual(response.status_code, 403)


class PeopleGroupInstancePermissionTestCase(JwtAPITestCase):
    def setUp(self) -> None:
        super().setUp()
        self.organization = OrganizationFactory()
        self.people_group = PeopleGroupFactory(organization=self.organization)
        self.user = UserFactory(groups=[self.people_group.get_managers()])
        self.client.force_authenticate(user=self.user)

    def test_create_people_group(self):
        parent = PeopleGroupFactory(organization=self.organization)
        payload = {
            "name": faker.name(),
            "description": faker.text(),
            "email": faker.email(),
            "parent": parent.id,
        }
        response = self.client.post(
            reverse("PeopleGroup-list", args=(self.organization.code,)), payload
        )
        self.assertEqual(response.status_code, 403)

    def test_retrieve_people_group(self):
        response = self.client.get(
            reverse(
                "PeopleGroup-detail",
                args=(self.organization.code, self.people_group.pk),
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], self.people_group.name)

    def test_partial_update_people_group(self):
        payload = {
            "description": "update",
        }
        response = self.client.patch(
            reverse(
                "PeopleGroup-detail",
                args=(self.organization.code, self.people_group.pk),
            ),
            payload,
        )
        self.assertEqual(response.status_code, 200)

    def test_destroy_people_group(self):
        response = self.client.delete(
            reverse(
                "PeopleGroup-detail",
                args=(self.organization.code, self.people_group.pk),
            )
        )
        self.assertEqual(response.status_code, 204)

    def test_add_members(self):
        user = UserFactory().keycloak_id
        payload = {
            PeopleGroup.DefaultGroup.MEMBERS: [user],
        }
        response = self.client.post(
            reverse(
                "PeopleGroup-add-member",
                args=(self.organization.code, self.people_group.pk),
            ),
            payload,
        )
        self.assertEqual(response.status_code, 204)

    def test_remove_members(self):
        user = UserFactory()
        self.people_group.members.add(user)
        payload = {
            "users": [user.keycloak_id],
        }
        response = self.client.post(
            reverse(
                "PeopleGroup-remove-member",
                args=(self.organization.code, self.people_group.pk),
            ),
            payload,
        )
        self.assertEqual(response.status_code, 204)

    def test_add_featured_project(self):
        project = ProjectFactory()
        project.members.add(self.user)

        payload = {"featured_projects": [project.id]}
        response = self.client.post(
            reverse(
                "PeopleGroup-add-featured-project",
                args=(self.organization.code, self.people_group.pk),
            ),
            payload,
        )
        self.assertEqual(response.status_code, 204)

    def test_remove_featured_project(self):
        project = ProjectFactory()
        self.people_group.featured_projects.add(project)
        project.members.add(self.user)

        payload = {"project": project.id}
        response = self.client.post(
            reverse(
                "PeopleGroup-remove-featured-project",
                args=(self.organization.code, self.people_group.pk),
            ),
            payload,
        )
        self.assertEqual(response.status_code, 204)


class PeopleGroupBasePermissionTestCase(JwtAPITestCase):
    def setUp(self):
        super().setUp()
        self.organization = OrganizationFactory()
        self.user = UserFactory(
            permissions=[
                ("accounts.view_peoplegroup", None),
                ("accounts.add_peoplegroup", None),
                ("accounts.change_peoplegroup", None),
                ("accounts.delete_peoplegroup", None),
            ]
        )
        self.client.force_authenticate(user=self.user)

    def test_create_people_group(self):
        parent = PeopleGroupFactory(organization=self.organization)
        payload = {
            "name": faker.name(),
            "description": faker.text(),
            "email": faker.email(),
            "parent": parent.id,
        }
        response = self.client.post(
            reverse("PeopleGroup-list", args=(self.organization.code,)), payload
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["name"], payload["name"])
        self.assertEqual(response.data["description"], payload["description"])
        self.assertEqual(response.data["email"], payload["email"])
        self.assertEqual(response.data["organization"], self.organization.code)
        self.assertEqual(response.data["hierarchy"][0]["id"], parent.id)

    def test_list_people_group(self):
        groups = PeopleGroupFactory.create_batch(3, organization=self.organization)
        response = self.client.get(
            f"{reverse('PeopleGroup-list', args=(self.organization.code,))}?is_root=false"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 3)
        self.assertEqual(
            {item["id"] for item in response.json()["results"]},
            {item.id for item in groups},
        )

    def test_retrieve_people_group(self):
        people_group = PeopleGroupFactory(organization=self.organization)
        response = self.client.get(
            reverse(
                "PeopleGroup-detail", args=(self.organization.code, people_group.pk)
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], people_group.name)

    def test_partial_update_people_group(self):
        people_group = PeopleGroupFactory(organization=self.organization)
        payload = {
            "description": "update",
        }
        response = self.client.patch(
            reverse(
                "PeopleGroup-detail", args=(self.organization.code, people_group.pk)
            ),
            payload,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["description"], payload["description"])

    def test_destroy_people_group(self):
        people_group = PeopleGroupFactory(organization=self.organization)
        response = self.client.delete(
            reverse(
                "PeopleGroup-detail", args=(self.organization.code, people_group.pk)
            )
        )
        self.assertEqual(response.status_code, 204)

    def test_add_members(self):
        user = UserFactory().keycloak_id
        people_group = PeopleGroupFactory(organization=self.organization)
        payload = {
            PeopleGroup.DefaultGroup.MEMBERS: [user],
        }
        response = self.client.post(
            reverse(
                "PeopleGroup-add-member",
                args=(self.organization.code, people_group.pk),
            ),
            payload,
        )
        self.assertEqual(response.status_code, 204)

    def test_remove_members(self):
        people_group = PeopleGroupFactory(organization=self.organization)
        user = UserFactory()
        people_group.managers.add(user)
        payload = {
            "users": [user.keycloak_id],
        }
        response = self.client.post(
            reverse(
                "PeopleGroup-remove-member",
                args=(self.organization.code, people_group.pk),
            ),
            payload,
        )
        self.assertEqual(response.status_code, 204)

    def test_add_featured_project(self):
        people_group = PeopleGroupFactory(organization=self.organization)
        project = ProjectFactory()
        project.members.add(self.user)

        payload = {"featured_projects": [project.id]}
        response = self.client.post(
            reverse(
                "PeopleGroup-add-featured-project",
                args=(self.organization.code, people_group.pk),
            ),
            payload,
        )
        self.assertEqual(response.status_code, 204)

    def test_remove_featured_project(self):
        people_group = PeopleGroupFactory(organization=self.organization)
        project = ProjectFactory()
        people_group.featured_projects.add(project)
        project.members.add(self.user)

        payload = {"project": project.id}
        response = self.client.post(
            reverse(
                "PeopleGroup-remove-featured-project",
                args=(self.organization.code, people_group.pk),
            ),
            payload,
        )
        self.assertEqual(response.status_code, 204)


class PeopleGroupOrgPermissionTestCase(JwtAPITestCase):
    def setUp(self):
        super().setUp()
        self.organization = OrganizationFactory()
        self.user = UserFactory(groups=[self.organization.get_admins()])
        self.client.force_authenticate(user=self.user)

    def test_create_people_group(self):
        parent = PeopleGroupFactory(organization=self.organization)
        payload = {
            "name": faker.name(),
            "description": faker.text(),
            "email": faker.email(),
            "parent": parent.id,
        }
        response = self.client.post(
            reverse("PeopleGroup-list", args=(self.organization.code,)), payload
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["name"], payload["name"])
        self.assertEqual(response.data["description"], payload["description"])
        self.assertEqual(response.data["email"], payload["email"])
        self.assertEqual(response.data["organization"], self.organization.code)
        self.assertEqual(response.data["hierarchy"][0]["id"], parent.id)

    def test_list_people_group(self):
        groups = PeopleGroupFactory.create_batch(3, organization=self.organization)
        response = self.client.get(
            f"{reverse('PeopleGroup-list', args=(self.organization.code,))}?is_root=false"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["count"], 3)
        self.assertEqual(
            {item["id"] for item in response.json()["results"]},
            {item.id for item in groups},
        )

    def test_retrieve_people_group(self):
        people_group = PeopleGroupFactory(organization=self.organization)
        response = self.client.get(
            reverse(
                "PeopleGroup-detail", args=(self.organization.code, people_group.pk)
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["name"], people_group.name)

    def test_partial_update_people_group(self):
        people_group = PeopleGroupFactory(organization=self.organization)
        payload = {
            "description": "update",
        }
        response = self.client.patch(
            reverse(
                "PeopleGroup-detail", args=(self.organization.code, people_group.pk)
            ),
            payload,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["description"], payload["description"])

    def test_destroy_people_group(self):
        people_group = PeopleGroupFactory(organization=self.organization)
        response = self.client.delete(
            reverse(
                "PeopleGroup-detail", args=(self.organization.code, people_group.pk)
            )
        )
        self.assertEqual(response.status_code, 204)

    def test_add_members(self):
        user = UserFactory().keycloak_id
        people_group = PeopleGroupFactory(organization=self.organization)
        payload = {
            PeopleGroup.DefaultGroup.MEMBERS: [user],
        }
        response = self.client.post(
            reverse(
                "PeopleGroup-add-member",
                args=(self.organization.code, people_group.pk),
            ),
            payload,
        )
        self.assertEqual(response.status_code, 204)

    def test_remove_members(self):
        people_group = PeopleGroupFactory(organization=self.organization)
        user = UserFactory()
        people_group.members.add(user)
        payload = {
            "users": [user.keycloak_id],
        }
        response = self.client.post(
            reverse(
                "PeopleGroup-remove-member",
                args=(self.organization.code, people_group.pk),
            ),
            payload,
        )
        self.assertEqual(response.status_code, 204)

    def test_add_featured_project(self):
        people_group = PeopleGroupFactory(organization=self.organization)
        project = ProjectFactory()
        project.members.add(self.user)

        payload = {"featured_projects": [project.id]}
        response = self.client.post(
            reverse(
                "PeopleGroup-add-featured-project",
                args=(self.organization.code, people_group.pk),
            ),
            payload,
        )
        self.assertEqual(response.status_code, 204)

    def test_remove_featured_project(self):
        people_group = PeopleGroupFactory(organization=self.organization)
        project = ProjectFactory()
        people_group.featured_projects.add(project)
        project.members.add(self.user)

        payload = {"project": project.id}
        response = self.client.post(
            reverse(
                "PeopleGroup-remove-featured-project",
                args=(self.organization.code, people_group.pk),
            ),
            payload,
        )
        self.assertEqual(response.status_code, 204)


class PeopleGroupValidationTestCase(JwtAPITestCase):
    def setUp(self):
        super().setUp()
        self.organization = OrganizationFactory()
        self.user = UserFactory(
            permissions=[
                ("accounts.view_peoplegroup", None),
                ("accounts.add_peoplegroup", None),
                ("accounts.change_peoplegroup", None),
                ("accounts.delete_peoplegroup", None),
            ]
        )
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

    def test_unexistant_organization(self):
        payload = {
            "name": faker.name(),
            "description": faker.text(),
            "email": faker.email(),
        }
        response = self.client.post(
            reverse("PeopleGroup-list", args=("unexistant",)), payload
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["detail"], "Not found.")

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

    def test_root_group_creation(self):
        organization = OrganizationFactory()
        root_people_group = PeopleGroup.objects.filter(
            organization=organization, is_root=True
        )
        assert root_people_group.exists()
        assert root_people_group.count() == 1

    def test_give_root_group_a_parent(self):
        organization = OrganizationFactory()
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
        organization = OrganizationFactory()
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
        organization = OrganizationFactory()
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


class PeopleGroupTestCase(JwtAPITestCase):
    def test_create_with_members(self):
        organization = OrganizationFactory()
        parent = PeopleGroupFactory(organization=organization)
        members = UserFactory.create_batch(3)
        managers = UserFactory.create_batch(3)
        payload = {
            "name": faker.name(),
            "description": faker.text(),
            "email": faker.email(),
            "parent": parent.id,
            "team": {
                "members": [m.keycloak_id for m in members],
                "managers": [r.keycloak_id for r in managers],
            },
        }
        user = UserFactory(permissions=[("accounts.add_peoplegroup", None)])
        self.client.force_authenticate(user)
        response = self.client.post(
            reverse("PeopleGroup-list", args=(organization.code,)),
            payload,
        )
        assert response.status_code == 201
        people_group = PeopleGroup.objects.get(id=response.json()["id"])
        assert all(member in people_group.members.all() for member in members)
        assert all(manager in people_group.managers.all() for manager in managers)

    def test_retrieve_members(self):
        people_group = PeopleGroupFactory(
            publication_status=PeopleGroup.PublicationStatus.PUBLIC
        )
        leaders_managers = UserFactory.create_batch(5)
        managers = UserFactory.create_batch(5)
        leaders_members = UserFactory.create_batch(5)
        members = UserFactory.create_batch(5)

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

        batch_1 = results[:5]
        batch_1_ids = [user["keycloak_id"] for user in batch_1]
        leaders_managers_ids = [user.keycloak_id for user in leaders_managers]
        assert leaders_managers_ids.sort() == batch_1_ids.sort()
        assert all(user["is_manager"] is True for user in batch_1)
        assert all(user["is_leader"] is True for user in batch_1)

        batch_2 = results[5:10]
        batch_2_ids = [user["keycloak_id"] for user in batch_2]
        leaders_members_ids = [user.keycloak_id for user in leaders_members]
        assert leaders_members_ids.sort() == batch_2_ids.sort()
        assert all(user["is_manager"] is False for user in batch_2)
        assert all(user["is_leader"] is True for user in batch_2)

        batch_3 = results[10:15]
        batch_3_ids = [user["keycloak_id"] for user in batch_3]
        managers_ids = [user.keycloak_id for user in managers]
        assert managers_ids.sort() == batch_3_ids.sort()
        assert all(user["is_manager"] is True for user in batch_3)
        assert all(user["is_leader"] is False for user in batch_3)

        batch_4 = results[15:]
        batch_4_ids = [user["keycloak_id"] for user in batch_4]
        members_ids = [user.keycloak_id for user in members]
        assert members_ids.sort() == batch_4_ids.sort()
        assert all(user["is_manager"] is False for user in batch_4)
        assert all(user["is_leader"] is False for user in batch_4)

    def test_retrieve_projects(self):
        people_group = PeopleGroupFactory(
            publication_status=PeopleGroup.PublicationStatus.PUBLIC
        )
        member = UserFactory()
        people_group.members.add(member)

        members_public_projects = ProjectFactory.create_batch(3)
        members_private_projects = ProjectFactory.create_batch(
            3, publication_status=Project.PublicationStatus.PRIVATE
        )
        members_featured_public_projects = ProjectFactory.create_batch(3)

        featured_public_projects = ProjectFactory.create_batch(3)
        featured_private_projects = ProjectFactory.create_batch(
            3, publication_status=Project.PublicationStatus.PRIVATE
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
        assert len(results) == 9

        nine_first = results[:6]
        featured_projects_ids = [project.id for project in featured_projects]
        nine_first_ids = [project["id"] for project in nine_first]
        assert featured_projects_ids.sort() == nine_first_ids.sort()
        nine_first_projects = [project["is_featured"] is True for project in nine_first]
        assert all(nine_first_projects) is True

        nine_last = results[-3:]
        member_projects_ids = [project.id for project in member_projects]
        nine_last_ids = [project["id"] for project in nine_last]
        assert member_projects_ids.sort() == nine_last_ids.sort()
        nine_last_projects = [project["is_featured"] is True for project in nine_last]
        assert all(nine_last_projects) is False

    def test_root_group_is_default_parent(self):
        organization = OrganizationFactory()
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
            publication_status=PeopleGroup.PublicationStatus.PUBLIC
        )
        self.client.force_authenticate(
            UserFactory(permissions=[("accounts.change_peoplegroup", None)])
        )
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
            publication_status=PeopleGroup.PublicationStatus.PUBLIC
        )
        self.client.force_authenticate(
            UserFactory(permissions=[("accounts.change_peoplegroup", None)])
        )
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
            publication_status=PeopleGroup.PublicationStatus.PUBLIC
        )
        self.client.force_authenticate(
            UserFactory(permissions=[("accounts.change_peoplegroup", None)])
        )
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
