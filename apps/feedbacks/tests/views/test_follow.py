from django.urls import reverse
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.commons.test import JwtAPITestCase
from apps.feedbacks.factories import FollowFactory
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory
from apps.projects.models import Project


class FollowTestCaseNoPermission(JwtAPITestCase):
    def test_create_no_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        user = UserFactory()
        user.groups.clear()
        payload = {"project_id": project.id}
        self.client.force_authenticate(user)
        project_response = self.client.post(
            reverse("Followed-list", kwargs={"project_id": project.id}), data=payload
        )
        user_response = self.client.post(
            reverse("Follower-list", kwargs={"user_keycloak_id": user.keycloak_id}),
            data=payload,
        )
        self.assertEqual(
            project_response.status_code,
            status.HTTP_403_FORBIDDEN,
            project_response.json(),
        )
        self.assertEqual(
            user_response.status_code,
            status.HTTP_403_FORBIDDEN,
            user_response.json(),
        )

    def test_create_many_no_permission(self):
        project1 = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        project2 = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        project3 = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        user = UserFactory()
        user.groups.clear()
        payload = {
            "follows": [
                {"project_id": project1.id},
                {"project_id": project2.id},
                {"project_id": project3.id},
            ]
        }

        self.client.force_authenticate(user)
        user_response = self.client.post(
            reverse("Follower-list", kwargs={"user_keycloak_id": user.keycloak_id}),
            data=payload,
        )

        self.assertEqual(
            user_response.status_code,
            status.HTTP_403_FORBIDDEN,
            user_response.json(),
        )

    def test_list_base_permission(self):
        organization = OrganizationFactory()
        project1 = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        project2 = ProjectFactory(publication_status=Project.PublicationStatus.PRIVATE)
        project3 = ProjectFactory(publication_status=Project.PublicationStatus.ORG)
        organization.projects.add(project1, project2, project3)
        follower1 = UserFactory()
        follower2 = UserFactory()
        follower3 = UserFactory()
        follower123 = UserFactory()
        FollowFactory(follower=follower1, project=project1)
        FollowFactory(follower=follower2, project=project2)
        FollowFactory(follower=follower3, project=project3)
        FollowFactory(follower=follower123, project=project1)
        FollowFactory(follower=follower123, project=project2)
        FollowFactory(follower=follower123, project=project3)

        self.client.force_authenticate(UserFactory())
        response = self.client.get(
            reverse("Followed-list", kwargs={"project_id": project1.id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        content = response.json()
        self.assertEqual(content["count"], 2)
        self.assertEqual(content["results"][0]["project"]["id"], project1.id)
        self.assertEqual(content["results"][0]["follower"]["id"], follower123.id)
        self.assertEqual(content["results"][1]["project"]["id"], project1.id)
        self.assertEqual(content["results"][1]["follower"]["id"], follower1.id)

        response = self.client.get(
            reverse("Followed-list", kwargs={"project_id": project2.id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        content = response.json()
        self.assertEqual(content["count"], 0)

        response = self.client.get(
            reverse("Follower-list", kwargs={"user_keycloak_id": follower1.keycloak_id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["project"]["id"], project1.id)
        self.assertEqual(content["results"][0]["follower"]["id"], follower1.id)

        response = self.client.get(
            reverse("Follower-list", kwargs={"user_keycloak_id": follower2.keycloak_id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        content = response.json()
        self.assertEqual(content["count"], 0)

        response = self.client.get(
            reverse(
                "Follower-list", kwargs={"user_keycloak_id": follower123.keycloak_id}
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["project"]["id"], project1.id)
        self.assertEqual(content["results"][0]["follower"]["id"], follower123.id)

    def test_destroy_base_permission(self):
        organization = OrganizationFactory()
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        organization.projects.add(project)
        follower = UserFactory()
        follow = FollowFactory(follower=follower, project=project)
        self.client.force_authenticate(UserFactory())
        project_response = self.client.delete(
            reverse(
                "Followed-detail", kwargs={"project_id": project.id, "id": follow.id}
            )
        )
        self.assertEqual(project_response.status_code, status.HTTP_403_FORBIDDEN)

        follow = FollowFactory(follower=follower, project=project)
        user_response = self.client.delete(
            reverse(
                "Follower-detail",
                kwargs={"user_keycloak_id": follower.keycloak_id, "id": follow.id},
            )
        )
        self.assertEqual(user_response.status_code, status.HTTP_403_FORBIDDEN)


class FollowTestCaseOwner(JwtAPITestCase):
    def test_list_owner(self):
        organization = OrganizationFactory()
        project1 = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        project2 = ProjectFactory(publication_status=Project.PublicationStatus.PRIVATE)
        project3 = ProjectFactory(publication_status=Project.PublicationStatus.ORG)
        organization.projects.add(project1, project2, project3)
        follower1 = UserFactory()
        follower2 = UserFactory()
        follower3 = UserFactory()
        follower123 = UserFactory()
        f1 = FollowFactory(follower=follower1, project=project1)
        FollowFactory(follower=follower2, project=project2)
        FollowFactory(follower=follower3, project=project3)
        FollowFactory(follower=follower123, project=project1)
        FollowFactory(follower=follower123, project=project2)
        FollowFactory(follower=follower123, project=project3)

        self.client.force_authenticate(f1.follower)
        response = self.client.get(
            reverse("Followed-list", kwargs={"project_id": project1.id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        content = response.json()
        self.assertEqual(content["count"], 2)
        self.assertEqual(content["results"][0]["project"]["id"], project1.id)
        self.assertEqual(content["results"][0]["follower"]["id"], follower123.id)
        self.assertEqual(content["results"][1]["project"]["id"], project1.id)
        self.assertEqual(content["results"][1]["follower"]["id"], follower1.id)

        response = self.client.get(
            reverse("Followed-list", kwargs={"project_id": project2.id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        content = response.json()
        self.assertEqual(content["count"], 0)

        response = self.client.get(
            reverse("Follower-list", kwargs={"user_keycloak_id": follower1.keycloak_id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["project"]["id"], project1.id)
        self.assertEqual(content["results"][0]["follower"]["id"], follower1.id)

        response = self.client.get(
            reverse("Follower-list", kwargs={"user_keycloak_id": follower2.keycloak_id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        content = response.json()
        self.assertEqual(content["count"], 0)

        response = self.client.get(
            reverse(
                "Follower-list", kwargs={"user_keycloak_id": follower123.keycloak_id}
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["project"]["id"], project1.id)
        self.assertEqual(content["results"][0]["follower"]["id"], follower123.id)

    def test_destroy_owner(self):
        organization = OrganizationFactory()
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        organization.projects.add(project)
        follower = UserFactory()
        follow = FollowFactory(follower=follower, project=project)
        self.client.force_authenticate(follower)
        project_response = self.client.delete(
            reverse(
                "Followed-detail", kwargs={"project_id": project.id, "id": follow.id}
            )
        )
        self.assertEqual(project_response.status_code, status.HTTP_204_NO_CONTENT)

        follow = FollowFactory(follower=follower, project=project)
        user_response = self.client.delete(
            reverse(
                "Follower-detail",
                kwargs={"user_keycloak_id": follower.keycloak_id, "id": follow.id},
            )
        )
        self.assertEqual(user_response.status_code, status.HTTP_204_NO_CONTENT)


class FollowTestCaseBasePermission(JwtAPITestCase):
    def test_create_base_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PRIVATE)
        user = UserFactory(permissions=[("projects.view_project", None)])
        payload = {"project_id": project.id}
        self.client.force_authenticate(user)
        project_response = self.client.post(
            reverse("Followed-list", kwargs={"project_id": project.id}), data=payload
        )
        user_response = self.client.post(
            reverse("Follower-list", kwargs={"user_keycloak_id": user.keycloak_id}),
            data=payload,
        )
        self.assertEqual(
            project_response.status_code,
            status.HTTP_201_CREATED,
            project_response.json(),
        )
        self.assertEqual(
            user_response.status_code, status.HTTP_201_CREATED, user_response.json()
        )

    def test_create_many_base_permission(self):
        project1 = ProjectFactory(publication_status=Project.PublicationStatus.PRIVATE)
        project2 = ProjectFactory(publication_status=Project.PublicationStatus.PRIVATE)
        project3 = ProjectFactory(publication_status=Project.PublicationStatus.PRIVATE)
        user = UserFactory()
        user = UserFactory(permissions=[("projects.view_project", None)])
        payload = {
            "follows": [
                {"project_id": project1.id},
                {"project_id": project2.id},
                {"project_id": project3.id},
            ]
        }
        self.client.force_authenticate(user)
        user_response = self.client.post(
            reverse(
                "Follower-follow-many", kwargs={"user_keycloak_id": user.keycloak_id}
            ),
            data=payload,
        )
        self.assertEqual(
            user_response.status_code, status.HTTP_201_CREATED, user_response.json()
        )

    def test_list_base_permission(self):
        organization = OrganizationFactory()
        project1 = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        project2 = ProjectFactory(publication_status=Project.PublicationStatus.PRIVATE)
        project3 = ProjectFactory(publication_status=Project.PublicationStatus.ORG)
        organization.projects.add(project1, project2, project3)
        follower1 = UserFactory()
        follower2 = UserFactory()
        follower3 = UserFactory()
        follower123 = UserFactory()
        FollowFactory(follower=follower1, project=project1)
        FollowFactory(follower=follower2, project=project2)
        FollowFactory(follower=follower3, project=project3)
        FollowFactory(follower=follower123, project=project1)
        FollowFactory(follower=follower123, project=project2)
        FollowFactory(follower=follower123, project=project3)

        user = UserFactory()
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("Followed-list", kwargs={"project_id": project1.id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        content = response.json()
        self.assertEqual(content["count"], 2)
        self.assertEqual(content["results"][0]["project"]["id"], project1.id)
        self.assertEqual(content["results"][0]["follower"]["id"], follower123.id)
        self.assertEqual(content["results"][1]["project"]["id"], project1.id)
        self.assertEqual(content["results"][1]["follower"]["id"], follower1.id)

        response = self.client.get(
            reverse("Followed-list", kwargs={"project_id": project2.id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        content = response.json()
        self.assertEqual(content["count"], 0)

        response = self.client.get(
            reverse("Follower-list", kwargs={"user_keycloak_id": follower1.keycloak_id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["project"]["id"], project1.id)
        self.assertEqual(content["results"][0]["follower"]["id"], follower1.id)

        response = self.client.get(
            reverse("Follower-list", kwargs={"user_keycloak_id": follower2.keycloak_id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        content = response.json()
        self.assertEqual(content["count"], 0)

        response = self.client.get(
            reverse(
                "Follower-list", kwargs={"user_keycloak_id": follower123.keycloak_id}
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["project"]["id"], project1.id)
        self.assertEqual(content["results"][0]["follower"]["id"], follower123.id)

    def test_destroy_base_permission(self):
        organization = OrganizationFactory()
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        organization.projects.add(project)
        follower = UserFactory()
        follow = FollowFactory(follower=follower, project=project)
        user = UserFactory(permissions=[("feedbacks.delete_follow", None)])
        self.client.force_authenticate(user)
        project_response = self.client.delete(
            reverse(
                "Followed-detail", kwargs={"project_id": project.id, "id": follow.id}
            )
        )
        self.assertEqual(project_response.status_code, status.HTTP_204_NO_CONTENT)

        follow = FollowFactory(follower=follower, project=project)
        user_response = self.client.delete(
            reverse(
                "Follower-detail",
                kwargs={"user_keycloak_id": follower.keycloak_id, "id": follow.id},
            )
        )
        self.assertEqual(user_response.status_code, status.HTTP_204_NO_CONTENT)


class FollowTestCaseProjectPermission(JwtAPITestCase):
    def test_create_project_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PRIVATE)
        user = UserFactory(permissions=[("projects.view_project", project)])
        payload = {"project_id": project.id}
        self.client.force_authenticate(user)
        project_response = self.client.post(
            reverse("Followed-list", kwargs={"project_id": project.id}), data=payload
        )
        user_response = self.client.post(
            reverse("Follower-list", kwargs={"user_keycloak_id": user.keycloak_id}),
            data=payload,
        )
        self.assertEqual(
            project_response.status_code,
            status.HTTP_201_CREATED,
            project_response.json(),
        )
        self.assertEqual(
            user_response.status_code, status.HTTP_201_CREATED, user_response.json()
        )

    def test_create_many_project_permission(self):
        project1 = ProjectFactory(publication_status=Project.PublicationStatus.PRIVATE)
        project2 = ProjectFactory(publication_status=Project.PublicationStatus.PRIVATE)
        project3 = ProjectFactory(publication_status=Project.PublicationStatus.PRIVATE)
        user = UserFactory(
            permissions=[
                ("projects.view_project", project1),
                ("projects.view_project", project2),
                ("projects.view_project", project3),
            ]
        )
        payload = {
            "follows": [
                {"project_id": project1.id},
                {"project_id": project2.id},
                {"project_id": project3.id},
            ]
        }
        self.client.force_authenticate(user)
        user_response = self.client.post(
            reverse(
                "Follower-follow-many", kwargs={"user_keycloak_id": user.keycloak_id}
            ),
            data=payload,
        )
        self.assertEqual(
            user_response.status_code, status.HTTP_201_CREATED, user_response.json()
        )

    def test_list_project_permission(self):
        organization = OrganizationFactory()
        project1 = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        project2 = ProjectFactory(publication_status=Project.PublicationStatus.PRIVATE)
        project3 = ProjectFactory(publication_status=Project.PublicationStatus.ORG)
        organization.projects.add(project1, project2, project3)
        follower1 = UserFactory(permissions=[("projects.view_project", project1)])
        follower2 = UserFactory(permissions=[("projects.view_project", project2)])
        follower3 = UserFactory(permissions=[("projects.view_project", project3)])
        follower123 = UserFactory(
            permissions=[
                ("projects.view_project", project1),
                ("projects.view_project", project2),
                ("projects.view_project", project3),
            ]
        )
        FollowFactory(follower=follower1, project=project1)
        FollowFactory(follower=follower2, project=project2)
        FollowFactory(follower=follower3, project=project3)
        FollowFactory(follower=follower123, project=project1)
        FollowFactory(follower=follower123, project=project2)
        FollowFactory(follower=follower123, project=project3)

        user = UserFactory()
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("Followed-list", kwargs={"project_id": project1.id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        content = response.json()
        self.assertEqual(content["count"], 2)
        self.assertEqual(content["results"][0]["project"]["id"], project1.id)
        self.assertEqual(content["results"][0]["follower"]["id"], follower123.id)
        self.assertEqual(content["results"][1]["project"]["id"], project1.id)
        self.assertEqual(content["results"][1]["follower"]["id"], follower1.id)

        response = self.client.get(
            reverse("Followed-list", kwargs={"project_id": project2.id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        content = response.json()
        self.assertEqual(content["count"], 0)

        response = self.client.get(
            reverse("Follower-list", kwargs={"user_keycloak_id": follower1.keycloak_id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["project"]["id"], project1.id)
        self.assertEqual(content["results"][0]["follower"]["id"], follower1.id)

        response = self.client.get(
            reverse("Follower-list", kwargs={"user_keycloak_id": follower2.keycloak_id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        content = response.json()
        self.assertEqual(content["count"], 0)

        response = self.client.get(
            reverse(
                "Follower-list", kwargs={"user_keycloak_id": follower123.keycloak_id}
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["project"]["id"], project1.id)
        self.assertEqual(content["results"][0]["follower"]["id"], follower123.id)

    def test_destroy_project_permission(self):
        organization = OrganizationFactory()
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        user = UserFactory(permissions=[("projects.delete_follow", project)])
        organization.projects.add(project)
        follower = UserFactory()
        follow = FollowFactory(follower=follower, project=project)
        self.client.force_authenticate(user)
        project_response = self.client.delete(
            reverse(
                "Followed-detail", kwargs={"project_id": project.id, "id": follow.id}
            )
        )
        self.assertEqual(project_response.status_code, status.HTTP_204_NO_CONTENT)

        follow = FollowFactory(follower=follower, project=project)
        user_response = self.client.delete(
            reverse(
                "Follower-detail",
                kwargs={"user_keycloak_id": follower.keycloak_id, "id": follow.id},
            )
        )
        self.assertEqual(user_response.status_code, status.HTTP_204_NO_CONTENT)


class FollowTestCaseOrganizationPermission(JwtAPITestCase):
    def test_create_org_permission(self):
        organization = OrganizationFactory()
        user = UserFactory(permissions=[("organizations.view_project", organization)])
        project = ProjectFactory(publication_status=Project.PublicationStatus.PRIVATE)
        organization.projects.add(project)
        payload = {"project_id": project.id}
        self.client.force_authenticate(user)
        project_response = self.client.post(
            reverse("Followed-list", kwargs={"project_id": project.id}), data=payload
        )
        user_response = self.client.post(
            reverse("Follower-list", kwargs={"user_keycloak_id": user.keycloak_id}),
            data=payload,
        )
        self.assertEqual(
            project_response.status_code,
            status.HTTP_201_CREATED,
            project_response.json(),
        )
        self.assertEqual(
            user_response.status_code, status.HTTP_201_CREATED, user_response.json()
        )

    def test_create_many_org_permission(self):
        organization = OrganizationFactory()
        user = UserFactory(permissions=[("organizations.view_project", organization)])
        project1 = ProjectFactory(publication_status=Project.PublicationStatus.ORG)
        project2 = ProjectFactory(publication_status=Project.PublicationStatus.ORG)
        project3 = ProjectFactory(publication_status=Project.PublicationStatus.ORG)
        organization.projects.add(project1)
        organization.projects.add(project2)
        organization.projects.add(project3)
        payload = {
            "follows": [
                {"project_id": project1.id},
                {"project_id": project2.id},
                {"project_id": project3.id},
            ]
        }
        self.client.force_authenticate(user)

        user_response = self.client.post(
            reverse(
                "Follower-follow-many", kwargs={"user_keycloak_id": user.keycloak_id}
            ),
            data=payload,
        )

        self.assertEqual(
            user_response.status_code, status.HTTP_201_CREATED, user_response.json()
        )

    def test_list_org_permission(self):
        organization = OrganizationFactory()
        user = UserFactory()
        project1 = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        project2 = ProjectFactory(publication_status=Project.PublicationStatus.PRIVATE)
        project3 = ProjectFactory(publication_status=Project.PublicationStatus.ORG)
        organization.projects.add(project1, project2, project3)
        follower1 = UserFactory()
        follower2 = UserFactory()
        follower3 = UserFactory()
        follower123 = UserFactory()
        FollowFactory(follower=follower1, project=project1)
        FollowFactory(follower=follower2, project=project2)
        FollowFactory(follower=follower3, project=project3)
        FollowFactory(follower=follower123, project=project1)
        FollowFactory(follower=follower123, project=project2)
        FollowFactory(follower=follower123, project=project3)

        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("Followed-list", kwargs={"project_id": project1.id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        content = response.json()
        self.assertEqual(content["count"], 2)
        self.assertEqual(content["results"][0]["project"]["id"], project1.id)
        self.assertEqual(content["results"][0]["follower"]["id"], follower123.id)
        self.assertEqual(content["results"][1]["project"]["id"], project1.id)
        self.assertEqual(content["results"][1]["follower"]["id"], follower1.id)

        response = self.client.get(
            reverse("Followed-list", kwargs={"project_id": project2.id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        content = response.json()
        self.assertEqual(content["count"], 0)

        response = self.client.get(
            reverse("Follower-list", kwargs={"user_keycloak_id": follower1.keycloak_id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["project"]["id"], project1.id)
        self.assertEqual(content["results"][0]["follower"]["id"], follower1.id)

        response = self.client.get(
            reverse("Follower-list", kwargs={"user_keycloak_id": follower2.keycloak_id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        content = response.json()
        self.assertEqual(content["count"], 0)

        response = self.client.get(
            reverse(
                "Follower-list", kwargs={"user_keycloak_id": follower123.keycloak_id}
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["project"]["id"], project1.id)
        self.assertEqual(content["results"][0]["follower"]["id"], follower123.id)

    def test_destroy_org_permission(self):
        organization = OrganizationFactory()
        user = UserFactory(permissions=[("organizations.delete_follow", organization)])
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        organization.projects.add(project)
        follower = UserFactory()
        follow = FollowFactory(follower=follower, project=project)
        self.client.force_authenticate(user)
        project_response = self.client.delete(
            reverse(
                "Followed-detail", kwargs={"project_id": project.id, "id": follow.id}
            )
        )
        self.assertEqual(project_response.status_code, status.HTTP_204_NO_CONTENT)

        follow = FollowFactory(follower=follower, project=project)
        user_response = self.client.delete(
            reverse(
                "Follower-detail",
                kwargs={"user_keycloak_id": follower.keycloak_id, "id": follow.id},
            )
        )
        self.assertEqual(user_response.status_code, status.HTTP_204_NO_CONTENT)


class FollowTestCaseProjectStatusPermission(JwtAPITestCase):
    def test_create_public_project_status_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        user = UserFactory()
        payload = {
            "project_id": project.id,
        }
        self.client.force_authenticate(user)
        response = self.client.post(
            reverse("Followed-list", kwargs={"project_id": project.id}),
            data=payload,
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

    def test_create_many_project_status_permission(self):
        project1 = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        project2 = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        project3 = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        user = UserFactory()
        payload = {
            "follows": [
                {"project_id": project1.id},
                {"project_id": project2.id},
                {"project_id": project3.id},
            ]
        }
        self.client.force_authenticate(user)
        response = self.client.post(
            reverse(
                "Follower-follow-many",
                kwargs={"user_keycloak_id": user.keycloak_id},
            ),
            data=payload,
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

    def test_create_org_project_status_permission(self):
        organization = OrganizationFactory()
        project = ProjectFactory(
            publication_status=Project.PublicationStatus.ORG,
            organizations=[organization],
        )
        user = UserFactory(
            permissions=[("organizations.view_org_project", organization)]
        )
        payload = {
            "project_id": project.id,
        }
        self.client.force_authenticate(user)
        response = self.client.post(
            reverse("Followed-list", kwargs={"project_id": project.id}),
            data=payload,
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

    def test_create_many_org_status_permission(self):
        organization = OrganizationFactory()
        project1 = ProjectFactory(
            publication_status=Project.PublicationStatus.ORG,
            organizations=[organization],
        )
        project2 = ProjectFactory(
            publication_status=Project.PublicationStatus.ORG,
            organizations=[organization],
        )
        project3 = ProjectFactory(
            publication_status=Project.PublicationStatus.ORG,
            organizations=[organization],
        )
        user = UserFactory(
            permissions=[("organizations.view_org_project", organization)]
        )
        payload = {
            "follows": [
                {"project_id": project1.id},
                {"project_id": project2.id},
                {"project_id": project3.id},
            ]
        }
        self.client.force_authenticate(user)
        response = self.client.post(
            reverse(
                "Follower-follow-many",
                kwargs={"user_keycloak_id": user.keycloak_id},
            ),
            data=payload,
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
