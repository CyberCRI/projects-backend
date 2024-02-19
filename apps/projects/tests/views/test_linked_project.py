from django.urls import reverse
from faker import Faker
from parameterized import parameterized
from rest_framework import status

from apps.commons.test import JwtAPITestCase, TestRoles
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import LinkedProjectFactory, ProjectFactory

faker = Faker()


class CreateLinkedProjectTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.linked_project_1 = ProjectFactory(organizations=[cls.organization])
        cls.linked_project_2 = ProjectFactory(organizations=[cls.organization])

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_201_CREATED),
            (TestRoles.ORG_ADMIN, status.HTTP_201_CREATED),
            (TestRoles.ORG_FACILITATOR, status.HTTP_201_CREATED),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_MEMBER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_OWNER, status.HTTP_201_CREATED),
            (TestRoles.PROJECT_REVIEWER, status.HTTP_201_CREATED),
        ]
    )
    def test_create_linked_project(self, role, expected_code):
        project = ProjectFactory(organizations=[self.organization])
        user = self.get_parameterized_test_user(role, instances=[project])
        self.client.force_authenticate(user)
        payload = {
            "project_id": self.linked_project_1.id,
            "target_id": project.id,
        }
        response = self.client.post(
            reverse("LinkedProjects-list", args=(project.id,)), data=payload
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_201_CREATED:
            content = response.json()
            assert content["project"]["id"] == self.linked_project_1.id

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_ADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_FACILITATOR, status.HTTP_200_OK),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_MEMBER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_OWNER, status.HTTP_200_OK),
            (TestRoles.PROJECT_REVIEWER, status.HTTP_200_OK),
        ]
    )
    def test_create_many_linked_projects(self, role, expected_code):
        project = ProjectFactory(organizations=[self.organization])
        user = self.get_parameterized_test_user(role, instances=[project])
        self.client.force_authenticate(user)
        payload = {
            "projects": [
                {
                    "project_id": self.linked_project_1.id,
                    "target_id": project.id,
                },
                {
                    "project_id": self.linked_project_2.id,
                    "target_id": project.id,
                },
            ]
        }
        response = self.client.post(
            reverse("LinkedProjects-add-many", args=(project.id,)), data=payload
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_200_OK:
            content = response.json()
            assert {p["project"]["id"] for p in content["linked_projects"]} == {
                self.linked_project_1.id,
                self.linked_project_2.id,
            }


class DeleteLinkedProjectTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.linked_project_1 = ProjectFactory(organizations=[cls.organization])
        cls.linked_project_2 = ProjectFactory(organizations=[cls.organization])

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_ADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_FACILITATOR, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_MEMBER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_OWNER, status.HTTP_204_NO_CONTENT),
            (TestRoles.PROJECT_REVIEWER, status.HTTP_204_NO_CONTENT),
        ]
    )
    def test_delete_linked_project(self, role, expected_code):
        project = ProjectFactory(organizations=[self.organization])
        instance = LinkedProjectFactory(target=project, project=self.linked_project_1)
        user = self.get_parameterized_test_user(role, instances=[project])
        self.client.force_authenticate(user)
        response = self.client.delete(
            reverse("LinkedProjects-detail", args=(project.id, instance.id))
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_204_NO_CONTENT:
            assert not project.linked_projects.filter(id=instance.id).exists()

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_ADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_FACILITATOR, status.HTTP_200_OK),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_MEMBER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_OWNER, status.HTTP_200_OK),
            (TestRoles.PROJECT_REVIEWER, status.HTTP_200_OK),
        ]
    )
    def test_delete_many_linked_projects(self, role, expected_code):
        project = ProjectFactory(organizations=[self.organization])
        user = self.get_parameterized_test_user(role, instances=[project])
        self.client.force_authenticate(user)
        instance_1 = LinkedProjectFactory(target=project, project=self.linked_project_1)
        instance_2 = LinkedProjectFactory(target=project, project=self.linked_project_2)
        payload = {"project_ids": [self.linked_project_1.id, self.linked_project_2.id]}
        response = self.client.delete(
            reverse("LinkedProjects-delete-many", args=(project.id,)), data=payload
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_200_OK:
            assert not project.linked_projects.filter(id=instance_1.id).exists()
            assert not project.linked_projects.filter(id=instance_2.id).exists()
