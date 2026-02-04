from django.urls import reverse
from django.utils.timezone import make_aware
from faker import Faker
from parameterized import parameterized
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.commons.test import JwtAPITestCase, TestRoles
from apps.feedbacks.factories import CommentFactory
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory
from apps.projects.models import Project

faker = Faker()


class ListCommentTestCase(JwtAPITestCase):
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
        cls.public_comment = CommentFactory(project=cls.public_project)
        cls.org_comment = CommentFactory(project=cls.org_project)
        cls.private_comment = CommentFactory(project=cls.private_project)
        cls.comments = {
            "public": cls.public_comment,
            "org": cls.org_comment,
            "private": cls.private_comment,
        }
        cls.replies = {
            "public": CommentFactory(
                project=cls.public_project, reply_on=cls.public_comment
            ),
            "org": CommentFactory(project=cls.org_project, reply_on=cls.org_comment),
            "private": CommentFactory(
                project=cls.private_project, reply_on=cls.private_comment
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
            (TestRoles.ORG_VIEWER, ("public", "org")),
            (TestRoles.PROJECT_MEMBER, ("public", "org", "private")),
            (TestRoles.PROJECT_OWNER, ("public", "org", "private")),
            (TestRoles.PROJECT_REVIEWER, ("public", "org", "private")),
        ]
    )
    def test_list_comments(self, role, retrieved_comments):
        for project_status, project in self.projects.items():
            user = self.get_parameterized_test_user(
                role, instances=[project], owned_instance=self.comments[project_status]
            )
            self.client.force_authenticate(user)
            response = self.client.get(
                reverse("Comment-list", args=(project.id,)),
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            content = response.json()["results"]
            if project_status in retrieved_comments:
                self.assertEqual(len(content), 1)
                self.assertEqual(content[0]["id"], self.comments[project_status].id)
                self.assertEqual(
                    content[0]["replies"][0]["id"], self.replies[project_status].id
                )
            else:
                self.assertEqual(len(content), 0)


class CreateCommentTestCase(JwtAPITestCase):
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
            (TestRoles.DEFAULT, ("public",)),
            (TestRoles.SUPERADMIN, ("public", "org", "private")),
            (TestRoles.ORG_ADMIN, ("public", "org", "private")),
            (TestRoles.ORG_FACILITATOR, ("public", "org", "private")),
            (TestRoles.ORG_USER, ("public", "org")),
            (TestRoles.ORG_VIEWER, ("public", "org")),
            (TestRoles.PROJECT_MEMBER, ("public", "org", "private")),
            (TestRoles.PROJECT_OWNER, ("public", "org", "private")),
            (TestRoles.PROJECT_REVIEWER, ("public", "org", "private")),
        ]
    )
    def test_create_comment(self, role, created_comments):
        user = self.get_parameterized_test_user(
            role, instances=list(self.projects.values())
        )
        self.client.force_authenticate(user)
        for publication_status, project in self.projects.items():
            payload = {
                "content": faker.text(),
                "project_id": project.id,
            }
            response = self.client.post(
                reverse("Comment-list", args=(project.id,)), data=payload
            )
            if publication_status in created_comments:
                self.assertEqual(response.status_code, status.HTTP_201_CREATED)
                self.assertEqual(response.json()["content"], payload["content"])
                self.assertEqual(response.json()["author"]["id"], user.id)
            else:
                self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_comment_anonymous(self):
        for project in self.projects.values():
            payload = {
                "content": faker.text(),
                "project_id": project.id,
            }
            response = self.client.post(
                reverse("Comment-list", args=(project.id,)), data=payload
            )
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class UpdateCommentTestCase(JwtAPITestCase):
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
    def test_update_comment(self, role, expected_code):
        user = self.get_parameterized_test_user(
            role, owned_instance=self.comment, instances=[self.project]
        )
        self.client.force_authenticate(user)
        payload = {"content": faker.text()}
        response = self.client.patch(
            reverse("Comment-detail", args=(self.project.id, self.comment.id)),
            data=payload,
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_200_OK:
            self.assertEqual(response.json()["content"], payload["content"])


class DeleteCommentTestCase(JwtAPITestCase):
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
    def test_delete_comment(self, role, expected_code):
        comment = CommentFactory(project=self.project)
        user = self.get_parameterized_test_user(
            role, owned_instance=comment, instances=[self.project]
        )
        self.client.force_authenticate(user)
        response = self.client.delete(
            reverse("Comment-detail", args=(self.project.id, comment.id)),
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_204_NO_CONTENT:
            response = self.client.get(
                reverse("Comment-list", args=(self.project.id,)),
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            content = response.json()["results"]
            self.assertNotIn(comment.id, [c["id"] for c in content])


class ReplyToCommentTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC
        )
        cls.user = UserFactory()

    def test_can_delete_reply(self):
        self.client.force_authenticate(self.user)
        comment = CommentFactory(project=self.project)
        reply = CommentFactory(project=self.project, reply_on=comment, author=self.user)
        response = self.client.delete(
            reverse("Comment-detail", args=(self.project.id, reply.id)),
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_can_patch_reply(self):
        self.client.force_authenticate(self.user)
        comment = CommentFactory(project=self.project)
        reply = CommentFactory(project=self.project, reply_on=comment, author=self.user)
        payload = {
            "content": faker.text(),
            "project_id": reply.project_id,
            "reply_on_id": reply.reply_on_id,
        }
        response = self.client.patch(
            reverse("Comment-detail", args=(self.project.id, reply.id)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["content"], payload["content"])

    def test_cannot_reply_to_themselves(self):
        self.client.force_authenticate(self.user)
        comment = CommentFactory(author=self.user, project=self.project)
        payload = {"reply_on_id": comment.id}
        response = self.client.patch(
            reverse("Comment-detail", args=(self.project.id, comment.id)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertApiValidationError(
            response,
            {"reply_on_id": ["A comment cannot be a reply to itself"]},
        )

    def test_cannot_reply_to_reply(self):
        self.client.force_authenticate(self.user)
        comment = CommentFactory(project=self.project)
        reply = CommentFactory(project=self.project, reply_on=comment, author=self.user)
        payload = {
            "content": faker.text(),
            "project_id": self.project.id,
            "reply_on_id": reply.id,
        }
        response = self.client.post(
            reverse("Comment-list", args=(self.project.id,)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertApiValidationError(
            response,
            {"reply_on_id": ["You cannot reply to a reply"]},
        )

    def test_deleted_with_replies_returned(self):
        self.client.force_authenticate(self.user)
        comment = CommentFactory(
            project=self.project, deleted_at=make_aware(faker.date_time())
        )
        CommentFactory(project=self.project, deleted_at=make_aware(faker.date_time()))
        CommentFactory(project=self.project, reply_on=comment)
        response = self.client.get(
            reverse("Comment-list", args=(self.project.id,)),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["id"], comment.id)
        self.assertEqual(content["results"][0]["content"], "<deleted comment>")
