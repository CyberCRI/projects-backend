from django.urls import reverse
from parameterized import parameterized
from rest_framework import status

from apps.commons.test import JwtAPITestCase, TestRoles
from apps.feedbacks.factories import CommentFactory
from apps.files.models import Image
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory
from apps.projects.models import Project


class RetrieveCommentImageTestCase(JwtAPITestCase):
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
        for project in cls.projects.values():
            comment = CommentFactory(project=project)
            image = cls.get_test_image(owner=comment.author)
            comment.images.add(image)

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_302_FOUND, "public"),
            (TestRoles.DEFAULT, status.HTTP_302_FOUND, "public"),
            (TestRoles.SUPERADMIN, status.HTTP_302_FOUND, "public"),
            (TestRoles.OWNER, status.HTTP_302_FOUND, "public"),
            (TestRoles.ORG_ADMIN, status.HTTP_302_FOUND, "public"),
            (TestRoles.ORG_FACILITATOR, status.HTTP_302_FOUND, "public"),
            (TestRoles.ORG_USER, status.HTTP_302_FOUND, "public"),
            (TestRoles.PROJECT_MEMBER, status.HTTP_302_FOUND, "public"),
            (TestRoles.PROJECT_OWNER, status.HTTP_302_FOUND, "public"),
            (TestRoles.PROJECT_REVIEWER, status.HTTP_302_FOUND, "public"),
            (TestRoles.ANONYMOUS, status.HTTP_404_NOT_FOUND, "org"),
            (TestRoles.DEFAULT, status.HTTP_404_NOT_FOUND, "org"),
            (TestRoles.SUPERADMIN, status.HTTP_302_FOUND, "org"),
            (TestRoles.OWNER, status.HTTP_302_FOUND, "org"),
            (TestRoles.ORG_ADMIN, status.HTTP_302_FOUND, "org"),
            (TestRoles.ORG_FACILITATOR, status.HTTP_302_FOUND, "org"),
            (TestRoles.ORG_USER, status.HTTP_302_FOUND, "org"),
            (TestRoles.PROJECT_MEMBER, status.HTTP_302_FOUND, "org"),
            (TestRoles.PROJECT_OWNER, status.HTTP_302_FOUND, "org"),
            (TestRoles.PROJECT_REVIEWER, status.HTTP_302_FOUND, "org"),
            (TestRoles.ANONYMOUS, status.HTTP_404_NOT_FOUND, "private"),
            (TestRoles.DEFAULT, status.HTTP_404_NOT_FOUND, "private"),
            (TestRoles.SUPERADMIN, status.HTTP_302_FOUND, "private"),
            (TestRoles.OWNER, status.HTTP_302_FOUND, "private"),
            (TestRoles.ORG_ADMIN, status.HTTP_302_FOUND, "private"),
            (TestRoles.ORG_FACILITATOR, status.HTTP_302_FOUND, "private"),
            (TestRoles.ORG_USER, status.HTTP_404_NOT_FOUND, "private"),
            (TestRoles.PROJECT_MEMBER, status.HTTP_302_FOUND, "private"),
            (TestRoles.PROJECT_OWNER, status.HTTP_302_FOUND, "private"),
            (TestRoles.PROJECT_REVIEWER, status.HTTP_302_FOUND, "private"),
        ]
    )
    def test_retrieve_comment_image(self, role, expected_code, project_status):
        project = self.projects[project_status]
        image = project.comments.first().images.first()
        user = self.get_parameterized_test_user(
            role, instances=[project], owned_instance=image
        )
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("Comment-images-detail", args=(project.id, image.id)),
        )
        assert response.status_code == expected_code


class CreateCommentImageTestCase(JwtAPITestCase):
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

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED, "public"),
            (TestRoles.DEFAULT, status.HTTP_201_CREATED, "public"),
            (TestRoles.SUPERADMIN, status.HTTP_201_CREATED, "public"),
            (TestRoles.ORG_ADMIN, status.HTTP_201_CREATED, "public"),
            (TestRoles.ORG_FACILITATOR, status.HTTP_201_CREATED, "public"),
            (TestRoles.ORG_USER, status.HTTP_201_CREATED, "public"),
            (TestRoles.PROJECT_MEMBER, status.HTTP_201_CREATED, "public"),
            (TestRoles.PROJECT_OWNER, status.HTTP_201_CREATED, "public"),
            (TestRoles.PROJECT_REVIEWER, status.HTTP_201_CREATED, "public"),
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED, "org"),
            (TestRoles.DEFAULT, status.HTTP_404_NOT_FOUND, "org"),
            (TestRoles.SUPERADMIN, status.HTTP_201_CREATED, "org"),
            (TestRoles.ORG_ADMIN, status.HTTP_201_CREATED, "org"),
            (TestRoles.ORG_FACILITATOR, status.HTTP_201_CREATED, "org"),
            (TestRoles.ORG_USER, status.HTTP_201_CREATED, "org"),
            (TestRoles.PROJECT_MEMBER, status.HTTP_201_CREATED, "org"),
            (TestRoles.PROJECT_OWNER, status.HTTP_201_CREATED, "org"),
            (TestRoles.PROJECT_REVIEWER, status.HTTP_201_CREATED, "org"),
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED, "private"),
            (TestRoles.DEFAULT, status.HTTP_404_NOT_FOUND, "private"),
            (TestRoles.SUPERADMIN, status.HTTP_201_CREATED, "private"),
            (TestRoles.ORG_ADMIN, status.HTTP_201_CREATED, "private"),
            (TestRoles.ORG_FACILITATOR, status.HTTP_201_CREATED, "private"),
            (TestRoles.ORG_USER, status.HTTP_404_NOT_FOUND, "private"),
            (TestRoles.PROJECT_MEMBER, status.HTTP_201_CREATED, "private"),
            (TestRoles.PROJECT_OWNER, status.HTTP_201_CREATED, "private"),
            (TestRoles.PROJECT_REVIEWER, status.HTTP_201_CREATED, "private"),
        ]
    )
    def test_create_comment_image(self, role, expected_code, project_status):
        instance = self.projects[project_status]
        user = self.get_parameterized_test_user(role, instances=[instance])
        self.client.force_authenticate(user)
        payload = {"file": self.get_test_image_file()}
        response = self.client.post(
            reverse("Comment-images-list", args=(instance.id,)),
            data=payload,
            format="multipart",
        )
        assert response.status_code == expected_code
        if expected_code == status.HTTP_201_CREATED:
            assert response.json()["static_url"] is not None


class UpdateCommentImageTestCase(JwtAPITestCase):
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
            (TestRoles.OWNER, status.HTTP_200_OK),
            (TestRoles.SUPERADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_ADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_FACILITATOR, status.HTTP_200_OK),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_MEMBER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_OWNER, status.HTTP_200_OK),
            (TestRoles.PROJECT_REVIEWER, status.HTTP_200_OK),
        ]
    )
    def test_update_comment_image(self, role, expected_code):
        comment = CommentFactory(project=self.project)
        image = self.get_test_image(owner=comment.author)
        comment.images.add(image)
        user = self.get_parameterized_test_user(
            role, owned_instance=image, instances=[self.project]
        )
        self.client.force_authenticate(user)
        payload = {
            "scale_x": 2.0,
            "scale_y": 2.0,
            "left": 1.0,
            "top": 1.0,
            "natural_ratio": 1.0,
        }
        response = self.client.patch(
            reverse(
                "Comment-images-detail",
                args=(self.project.id, image.id),
            ),
            data=payload,
            format="multipart",
        )
        assert response.status_code == expected_code
        if expected_code == status.HTTP_200_OK:
            assert response.json()["scale_x"] == payload["scale_x"]
            assert response.json()["scale_y"] == payload["scale_y"]
            assert response.json()["left"] == payload["left"]
            assert response.json()["top"] == payload["top"]
            assert response.json()["natural_ratio"] == payload["natural_ratio"]


class DeleteCommentImageTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[cls.organization],
        )
        cls.comment = CommentFactory(project=cls.project)

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.OWNER, status.HTTP_204_NO_CONTENT),
            (TestRoles.SUPERADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_ADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_FACILITATOR, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_MEMBER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_OWNER, status.HTTP_204_NO_CONTENT),
            (TestRoles.PROJECT_REVIEWER, status.HTTP_204_NO_CONTENT),
        ]
    )
    def test_delete_comment_image(self, role, expected_code):
        image = self.get_test_image(owner=self.comment.author)
        self.comment.images.add(image)
        user = self.get_parameterized_test_user(
            role, owned_instance=image, instances=[self.project]
        )
        self.client.force_authenticate(user)
        response = self.client.delete(
            reverse("Comment-images-detail", args=(self.project.id, image.id)),
        )
        assert response.status_code == expected_code
        if expected_code == status.HTTP_204_NO_CONTENT:
            assert not Image.objects.filter(id=image.id).exists()
