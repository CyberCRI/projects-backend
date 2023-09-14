from django.urls import reverse
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.commons.test import JwtAPITestCase
from apps.feedbacks.factories import ReviewFactory
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory
from apps.projects.models import Project


class ReviewTestCaseNoPermission(JwtAPITestCase):
    """Check that no permission can only read reviews"""

    def test_create_no_permission(self):
        project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            life_status=Project.LifeStatus.TO_REVIEW,
        )
        payload = {
            "project_id": project.id,
            "title": "Title",
            "description": "Description",
        }
        self.client.force_authenticate(UserFactory())
        response = self.client.post(
            reverse("Reviewed-list", kwargs={"project_id": project.id}), data=payload
        )
        self.assertEqual(
            response.status_code, status.HTTP_403_FORBIDDEN, response.json()
        )

    def test_retrieve_no_permission(self):
        organization = OrganizationFactory()
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        organization.projects.add(project)
        user = UserFactory()
        review = ReviewFactory(reviewer=user, project=project)
        self.client.force_authenticate(UserFactory())
        response = self.client.get(
            reverse(
                "Reviewed-detail", kwargs={"project_id": project.id, "id": review.id}
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        review = ReviewFactory(reviewer=user, project=project)
        response = self.client.get(
            reverse(
                "Reviewer-detail",
                kwargs={"user_keycloak_id": user.keycloak_id, "id": review.id},
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_no_permission(self):
        organization = OrganizationFactory()
        project1 = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        project2 = ProjectFactory(publication_status=Project.PublicationStatus.PRIVATE)
        project3 = ProjectFactory(publication_status=Project.PublicationStatus.ORG)
        organization.projects.add(project1, project2, project3)
        reviewer1 = UserFactory()
        reviewer2 = UserFactory()
        reviewer3 = UserFactory()
        reviewer123 = UserFactory()
        ReviewFactory(reviewer=reviewer1, project=project1)
        ReviewFactory(reviewer=reviewer2, project=project2)
        ReviewFactory(reviewer=reviewer3, project=project3)
        ReviewFactory(reviewer=reviewer123, project=project1)
        ReviewFactory(reviewer=reviewer123, project=project2)
        ReviewFactory(reviewer=reviewer123, project=project3)

        self.client.force_authenticate(UserFactory())
        response = self.client.get(
            reverse("Reviewed-list", kwargs={"project_id": project1.id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        content = response.json()
        self.assertEqual(content["count"], 2)
        self.assertEqual(content["results"][0]["reviewer"]["id"], reviewer1.id)
        self.assertEqual(content["results"][1]["reviewer"]["id"], reviewer123.id)

        response = self.client.get(
            reverse("Reviewed-list", kwargs={"project_id": project2.id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        content = response.json()
        self.assertEqual(content["count"], 0)

        response = self.client.get(
            reverse("Reviewer-list", kwargs={"user_keycloak_id": reviewer1.keycloak_id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["reviewer"]["id"], reviewer1.id)

        response = self.client.get(
            reverse("Reviewer-list", kwargs={"user_keycloak_id": reviewer2.keycloak_id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        content = response.json()
        self.assertEqual(content["count"], 0)

        response = self.client.get(
            reverse(
                "Reviewer-list", kwargs={"user_keycloak_id": reviewer123.keycloak_id}
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["reviewer"]["id"], reviewer123.id)

    def test_update_no_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        user = UserFactory()
        review = ReviewFactory(reviewer=user, project=project)
        payload = {
            "project_id": project.id,
            "title": "NewTitle",
            "description": review.description,
        }
        self.client.force_authenticate(UserFactory())
        url = reverse(
            "Reviewed-detail", kwargs={"project_id": project.id, "id": review.id}
        )
        response = self.client.put(url, data=payload)
        self.assertEqual(
            response.status_code, status.HTTP_403_FORBIDDEN, response.content
        )

    def test_partial_update_no_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        user = UserFactory()
        review = ReviewFactory(reviewer=user, project=project)
        payload = {"title": "NewTitle"}
        self.client.force_authenticate(UserFactory())
        url = reverse(
            "Reviewed-detail", kwargs={"project_id": project.id, "id": review.id}
        )
        response = self.client.patch(url, data=payload)
        self.assertEqual(
            response.status_code, status.HTTP_403_FORBIDDEN, response.content
        )

    def test_destroy_no_permission(self):
        organization = OrganizationFactory()
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        organization.projects.add(project)
        user = UserFactory()
        review = ReviewFactory(reviewer=user, project=project)
        self.client.force_authenticate(UserFactory())
        response = self.client.delete(
            reverse(
                "Reviewed-detail", kwargs={"project_id": project.id, "id": review.id}
            )
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        review = ReviewFactory(reviewer=user, project=project)
        response = self.client.delete(
            reverse(
                "Reviewer-detail",
                kwargs={"user_keycloak_id": user.keycloak_id, "id": review.id},
            )
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class ReviewTestCaseOwner(JwtAPITestCase):
    def test_update_owner(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        user = UserFactory()
        review = ReviewFactory(reviewer=user, project=project)
        payload = {
            "project_id": project.id,
            "title": "NewTitle",
            "description": review.description,
        }
        self.client.force_authenticate(user)
        url = reverse(
            "Reviewed-detail", kwargs={"project_id": project.id, "id": review.id}
        )
        response = self.client.put(url, data=payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

    def test_partial_update_owner(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        user = UserFactory()
        review = ReviewFactory(reviewer=user, project=project)
        payload = {"title": "NewTitle"}
        self.client.force_authenticate(user)
        url = reverse(
            "Reviewed-detail", kwargs={"project_id": project.id, "id": review.id}
        )
        response = self.client.patch(url, data=payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

    def test_destroy_owner(self):
        organization = OrganizationFactory()
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        organization.projects.add(project)
        user = UserFactory()
        review = ReviewFactory(reviewer=user, project=project)
        self.client.force_authenticate(user)
        response = self.client.delete(
            reverse(
                "Reviewed-detail", kwargs={"project_id": project.id, "id": review.id}
            )
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        review = ReviewFactory(reviewer=user, project=project)
        response = self.client.delete(
            reverse(
                "Reviewer-detail",
                kwargs={"user_keycloak_id": user.keycloak_id, "id": review.id},
            )
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class ReviewTestCaseBasePermission(JwtAPITestCase):
    def test_create_base_permission_wrong_status(self):
        project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            life_status=Project.LifeStatus.RUNNING,
        )
        payload = {
            "project_id": project.id,
            "title": "Title",
            "description": "Description",
        }
        user = UserFactory(permissions=[("feedbacks.add_review", None)])
        self.client.force_authenticate(user)
        response = self.client.post(
            reverse("Reviewed-list", kwargs={"project_id": project.id}), data=payload
        )
        self.assertEqual(
            response.status_code, status.HTTP_403_FORBIDDEN, response.json()
        )

    def test_create_base_permission(self):
        project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            life_status=Project.LifeStatus.TO_REVIEW,
        )
        payload = {
            "project_id": project.id,
            "title": "Title",
            "description": "Description",
        }
        user = UserFactory(permissions=[("feedbacks.add_review", None)])
        self.client.force_authenticate(user)
        response = self.client.post(
            reverse("Reviewed-list", kwargs={"project_id": project.id}), data=payload
        )
        self.assertEqual(
            response.status_code, status.HTTP_201_CREATED, response.content
        )

    def test_update_base_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        user = UserFactory()
        review = ReviewFactory(reviewer=user, project=project)
        payload = {
            "project_id": project.id,
            "title": "NewTitle",
            "description": review.description,
        }
        user = UserFactory(permissions=[("feedbacks.change_review", None)])
        self.client.force_authenticate(user)
        url = reverse(
            "Reviewed-detail", kwargs={"project_id": project.id, "id": review.id}
        )
        response = self.client.put(url, data=payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

    def test_partial_update_base_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        user = UserFactory()
        review = ReviewFactory(reviewer=user, project=project)
        payload = {"title": "NewTitle"}
        user = UserFactory(permissions=[("feedbacks.change_review", None)])
        self.client.force_authenticate(user)
        url = reverse(
            "Reviewed-detail", kwargs={"project_id": project.id, "id": review.id}
        )
        response = self.client.patch(url, data=payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

    def test_destroy_base_permission(self):
        organization = OrganizationFactory()
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        organization.projects.add(project)
        user = UserFactory()
        review = ReviewFactory(reviewer=user, project=project)
        user = UserFactory(permissions=[("feedbacks.delete_review", None)])
        self.client.force_authenticate(user)
        response = self.client.delete(
            reverse(
                "Reviewed-detail", kwargs={"project_id": project.id, "id": review.id}
            )
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        review = ReviewFactory(reviewer=user, project=project)
        response = self.client.delete(
            reverse(
                "Reviewer-detail",
                kwargs={"user_keycloak_id": user.keycloak_id, "id": review.id},
            )
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class ReviewTestCaseProjectPermission(JwtAPITestCase):
    def test_create_project_permission_wrong_status(self):
        project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            life_status=Project.LifeStatus.RUNNING,
        )
        payload = {
            "project_id": project.id,
            "title": "Title",
            "description": "Description",
        }
        user = UserFactory(permissions=[("projects.add_review", project)])
        self.client.force_authenticate(user)
        response = self.client.post(
            reverse("Reviewed-list", kwargs={"project_id": project.id}), data=payload
        )
        self.assertEqual(
            response.status_code, status.HTTP_403_FORBIDDEN, response.json()
        )

    def test_create_project_permission(self):
        project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            life_status=Project.LifeStatus.TO_REVIEW,
        )
        payload = {
            "project_id": project.id,
            "title": "Title",
            "description": "Description",
        }
        user = UserFactory(permissions=[("projects.add_review", project)])
        self.client.force_authenticate(user)
        response = self.client.post(
            reverse("Reviewed-list", kwargs={"project_id": project.id}), data=payload
        )
        self.assertEqual(
            response.status_code, status.HTTP_201_CREATED, response.content
        )

    def test_update_project_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        user = UserFactory()
        review = ReviewFactory(reviewer=user, project=project)
        payload = {
            "project_id": project.id,
            "title": "NewTitle",
            "description": review.description,
        }
        user = UserFactory(permissions=[("projects.change_review", project)])
        self.client.force_authenticate(user)
        url = reverse(
            "Reviewed-detail", kwargs={"project_id": project.id, "id": review.id}
        )
        response = self.client.put(url, data=payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

    def test_partial_update_project_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        user = UserFactory()
        review = ReviewFactory(reviewer=user, project=project)
        payload = {"title": "NewTitle"}
        user = UserFactory(permissions=[("projects.change_review", project)])
        self.client.force_authenticate(user)
        url = reverse(
            "Reviewed-detail", kwargs={"project_id": project.id, "id": review.id}
        )
        response = self.client.patch(url, data=payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

    def test_destroy_project_permission(self):
        organization = OrganizationFactory()
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        organization.projects.add(project)
        user = UserFactory()
        review = ReviewFactory(reviewer=user, project=project)
        user = UserFactory(permissions=[("projects.delete_review", project)])
        self.client.force_authenticate(user)
        response = self.client.delete(
            reverse(
                "Reviewed-detail", kwargs={"project_id": project.id, "id": review.id}
            )
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        review = ReviewFactory(reviewer=user, project=project)
        response = self.client.delete(
            reverse(
                "Reviewer-detail",
                kwargs={"user_keycloak_id": user.keycloak_id, "id": review.id},
            )
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class ReviewTestCaseOrganizationPermission(JwtAPITestCase):
    def test_create_org_permission_wrong_status(self):
        organization = OrganizationFactory()
        project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            life_status=Project.LifeStatus.RUNNING,
        )
        organization.projects.add(project)
        payload = {
            "project_id": project.id,
            "title": "Title",
            "description": "Description",
        }
        user = UserFactory(permissions=[("organizations.add_review", organization)])
        self.client.force_authenticate(user)
        response = self.client.post(
            reverse("Reviewed-list", kwargs={"project_id": project.id}), data=payload
        )
        self.assertEqual(
            response.status_code, status.HTTP_403_FORBIDDEN, response.json()
        )

    def test_create_org_permission(self):
        organization = OrganizationFactory()
        project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            life_status=Project.LifeStatus.TO_REVIEW,
        )
        organization.projects.add(project)
        payload = {
            "project_id": project.id,
            "title": "Title",
            "description": "Description",
        }
        user = UserFactory(permissions=[("organizations.add_review", organization)])
        self.client.force_authenticate(user)
        response = self.client.post(
            reverse("Reviewed-list", kwargs={"project_id": project.id}), data=payload
        )
        self.assertEqual(
            response.status_code, status.HTTP_201_CREATED, response.content
        )

    def test_update_org_permission(self):
        organization = OrganizationFactory()
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        organization.projects.add(project)
        user = UserFactory()
        review = ReviewFactory(reviewer=user, project=project)
        payload = {
            "project_id": project.id,
            "title": "NewTitle",
            "description": review.description,
        }
        user = UserFactory(permissions=[("organizations.change_review", organization)])
        self.client.force_authenticate(user)
        url = reverse(
            "Reviewed-detail", kwargs={"project_id": project.id, "id": review.id}
        )
        response = self.client.put(url, data=payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

    def test_partial_update_org_permission(self):
        organization = OrganizationFactory()
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        organization.projects.add(project)
        user = UserFactory()
        review = ReviewFactory(reviewer=user, project=project)
        payload = {"title": "NewTitle"}
        user = UserFactory(permissions=[("organizations.change_review", organization)])
        self.client.force_authenticate(user)
        url = reverse(
            "Reviewed-detail", kwargs={"project_id": project.id, "id": review.id}
        )
        response = self.client.patch(url, data=payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

    def test_destroy_org_permission(self):
        organization = OrganizationFactory()
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        organization.projects.add(project)
        user = UserFactory()
        review = ReviewFactory(reviewer=user, project=project)
        user = UserFactory(permissions=[("organizations.delete_review", organization)])
        self.client.force_authenticate(user)
        response = self.client.delete(
            reverse(
                "Reviewed-detail", kwargs={"project_id": project.id, "id": review.id}
            )
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        review = ReviewFactory(reviewer=user, project=project)
        response = self.client.delete(
            reverse(
                "Reviewer-detail",
                kwargs={"user_keycloak_id": user.keycloak_id, "id": review.id},
            )
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
