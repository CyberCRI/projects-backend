from django.urls import reverse
from faker import Faker
from parameterized import parameterized
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase, TestRoles
from apps.feedbacks.factories import ReviewFactory
from apps.feedbacks.models import Review
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory
from apps.projects.models import Project

faker = Faker()


class CreateReviewTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            life_status=Project.LifeStatus.TO_REVIEW,
            organizations=[cls.organization],
        )

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_201_CREATED),
            (TestRoles.ORG_ADMIN, status.HTTP_201_CREATED),
            (TestRoles.ORG_FACILITATOR, status.HTTP_403_FORBIDDEN),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_MEMBER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_OWNER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_REVIEWER, status.HTTP_201_CREATED),
        ]
    )
    def test_create_reviewed(self, role, expected_code):
        project = self.project
        user = self.get_parameterized_test_user(role, instances=[project])
        self.client.force_authenticate(user)
        payload = {
            "project_id": project.id,
            "title": faker.sentence(),
            "description": faker.text(),
        }
        response = self.client.post(
            reverse("Reviewed-list", args=(project.id,)), data=payload
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_201_CREATED:
            content = response.json()
            self.assertEqual(content["project_id"], project.id)
            self.assertEqual(content["reviewer"]["id"], user.id)
            self.assertEqual(content["title"], payload["title"])
            self.assertEqual(content["description"], payload["description"])


class UpdateReviewTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[cls.organization],
        )
        cls.review = ReviewFactory(project=cls.project)

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_200_OK),
            (TestRoles.OWNER, status.HTTP_200_OK),
            (TestRoles.ORG_ADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_FACILITATOR, status.HTTP_403_FORBIDDEN),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_MEMBER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_OWNER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_REVIEWER, status.HTTP_200_OK),
        ]
    )
    def test_update_reviewed(self, role, expected_code):
        user = self.get_parameterized_test_user(
            role, instances=[self.project], owned_instance=self.review
        )
        self.client.force_authenticate(user)
        payload = {
            "description": faker.text(),
        }
        response = self.client.patch(
            reverse("Reviewed-detail", args=(self.project.id, self.review.id)),
            data=payload,
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_200_OK:
            self.assertEqual(response.json()["description"], payload["description"])

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_200_OK),
            (TestRoles.OWNER, status.HTTP_200_OK),
            (TestRoles.ORG_ADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_FACILITATOR, status.HTTP_403_FORBIDDEN),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_MEMBER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_OWNER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_REVIEWER, status.HTTP_200_OK),
        ]
    )
    def test_update_reviewer(self, role, expected_code):
        user = self.get_parameterized_test_user(
            role, instances=[self.project], owned_instance=self.review
        )
        self.client.force_authenticate(user)
        payload = {
            "description": faker.text(),
        }
        response = self.client.patch(
            reverse("Reviewer-detail", args=(self.review.reviewer.id, self.review.id)),
            data=payload,
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_200_OK:
            self.assertEqual(response.json()["description"], payload["description"])


class ListReviewTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.public_project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[cls.organization],
        )
        cls.org_project = ProjectFactory(
            publication_status=Project.PublicationStatus.ORG,
            organizations=[cls.organization],
        )
        cls.private_project = ProjectFactory(
            publication_status=Project.PublicationStatus.PRIVATE,
            organizations=[cls.organization],
        )
        cls.projects = {
            "public": cls.public_project,
            "org": cls.org_project,
            "private": cls.private_project,
        }
        cls.reviewer = UserFactory()
        cls.reviews = {
            "public": ReviewFactory(project=cls.public_project, reviewer=cls.reviewer),
            "org": ReviewFactory(project=cls.org_project, reviewer=cls.reviewer),
            "private": ReviewFactory(
                project=cls.private_project, reviewer=cls.reviewer
            ),
        }

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, ("public",)),
            (TestRoles.DEFAULT, ("public",)),
            (TestRoles.SUPERADMIN, ("public", "org", "private")),
            (TestRoles.OWNER, ("public", "org", "private")),
            (TestRoles.ORG_ADMIN, ("public", "org", "private")),
            (TestRoles.ORG_FACILITATOR, ("public", "org", "private")),
            (TestRoles.ORG_USER, ("public", "org")),
            (TestRoles.PROJECT_MEMBER, ("public", "org", "private")),
            (TestRoles.PROJECT_OWNER, ("public", "org", "private")),
            (TestRoles.PROJECT_REVIEWER, ("public", "org", "private")),
        ]
    )
    def test_list_reviewed(self, role, retrieved_reviews):
        user = self.get_parameterized_test_user(
            role, instances=list(self.projects.values()), owned_instance=self.reviewer
        )
        self.client.force_authenticate(user)
        for project_status, project in self.projects.items():
            response = self.client.get(reverse("Reviewed-list", args=(project.id,)))
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            content = response.json()["results"]
            if project_status in retrieved_reviews:
                self.assertEqual(len(content), 1)
                self.assertEqual(content[0]["project_id"], project.id)
                self.assertEqual(content[0]["reviewer"]["id"], self.reviewer.id)
                self.assertEqual(
                    content[0]["description"], self.reviews[project_status].description
                )

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, ("public",)),
            (TestRoles.DEFAULT, ("public",)),
            (TestRoles.SUPERADMIN, ("public", "org", "private")),
            (TestRoles.OWNER, ("public", "org", "private")),
            (TestRoles.ORG_ADMIN, ("public", "org", "private")),
            (TestRoles.ORG_FACILITATOR, ("public", "org", "private")),
            (TestRoles.ORG_USER, ("public", "org")),
            (TestRoles.PROJECT_MEMBER, ("public", "org", "private")),
            (TestRoles.PROJECT_OWNER, ("public", "org", "private")),
            (TestRoles.PROJECT_REVIEWER, ("public", "org", "private")),
        ]
    )
    def test_list_reviewer(self, role, retrieved_reviews):
        user = self.get_parameterized_test_user(
            role, instances=list(self.projects.values()), owned_instance=self.reviewer
        )
        self.client.force_authenticate(user)
        response = self.client.get(reverse("Reviewer-list", args=(self.reviewer.id,)))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), len(retrieved_reviews))
        self.assertSetEqual(
            {review["id"] for review in content},
            {self.reviews[project_status].id for project_status in retrieved_reviews},
        )


class DestroyReviewTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[cls.organization],
        )

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.OWNER, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_ADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_FACILITATOR, status.HTTP_403_FORBIDDEN),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_MEMBER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_OWNER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_REVIEWER, status.HTTP_204_NO_CONTENT),
        ]
    )
    def test_delete_reviewed(self, role, expected_code):
        project = self.project
        review = ReviewFactory(project=self.project)
        user = self.get_parameterized_test_user(
            role, instances=[project], owned_instance=review
        )
        self.client.force_authenticate(user)
        response = self.client.delete(
            reverse("Reviewed-detail", args=(project.id, review.id))
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_204_NO_CONTENT:
            self.assertFalse(Review.objects.filter(id=review.id).exists())

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.OWNER, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_ADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_FACILITATOR, status.HTTP_403_FORBIDDEN),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_MEMBER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_OWNER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_REVIEWER, status.HTTP_204_NO_CONTENT),
        ]
    )
    def test_delete_reviewer(self, role, expected_code):
        project = self.project
        review = ReviewFactory(project=self.project)
        user = self.get_parameterized_test_user(
            role, instances=[project], owned_instance=review
        )
        self.client.force_authenticate(user)
        response = self.client.delete(
            reverse("Reviewer-detail", args=(review.reviewer.id, review.id))
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_204_NO_CONTENT:
            self.assertFalse(Review.objects.filter(id=review.id).exists())


class ValidateReviewTestCase(JwtAPITestCase):
    def test_create_wrong_status(self):
        project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            life_status=Project.LifeStatus.RUNNING,
        )
        payload = {
            "project_id": project.id,
            "title": faker.sentence(),
            "description": faker.text(),
        }
        user = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(user)
        response = self.client.post(
            reverse("Reviewed-list", args=(project.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class MiscReviewTestCase(JwtAPITestCase):
    def test_multiple_lookups(self):
        self.client.force_authenticate(UserFactory(groups=[get_superadmins_group()]))
        review = ReviewFactory()
        response = self.client.get(
            reverse("Reviewed-detail", args=(review.project.id, review.id)),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["id"], review.id)
        response = self.client.get(
            reverse("Reviewed-detail", args=(review.project.slug, review.id)),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["id"], review.id)
        response = self.client.get(
            reverse("Reviewer-detail", args=(review.reviewer.id, review.id)),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["id"], review.id)
        response = self.client.get(
            reverse("Reviewer-detail", args=(review.reviewer.slug, review.id)),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["id"], review.id)
        response = self.client.get(
            reverse("Reviewer-detail", args=(review.reviewer.keycloak_id, review.id)),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["id"], review.id)
