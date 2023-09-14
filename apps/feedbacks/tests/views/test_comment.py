from collections import defaultdict

from django.urls import reverse
from faker import Faker
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.commons.test import JwtAPITestCase
from apps.feedbacks.factories import CommentFactory
from apps.feedbacks.models import Comment
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory
from apps.projects.models import Project

FAKER = Faker()


class CommentTestCaseNoPermission(JwtAPITestCase):
    def test_create_no_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.ORG)
        payload = {
            "project_id": project.id,
            "content": FAKER.sentence(),
        }
        self.client.force_authenticate(UserFactory())
        response = self.client.post(
            reverse("Comment-list", kwargs={"project_id": project.id}), data=payload
        )
        self.assertEqual(
            response.status_code, status.HTTP_403_FORBIDDEN, response.json()
        )

    def test_retrieve_no_permission(self):
        organization = OrganizationFactory()
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        organization.projects.add(project)
        comment = CommentFactory(author=UserFactory(), project=project)
        self.client.force_authenticate(UserFactory())
        response = self.client.get(
            reverse(
                "Comment-detail", kwargs={"id": comment.id, "project_id": project.id}
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

    def test_list_no_permission(self):
        organization = OrganizationFactory()
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        organization.projects.add(project)
        CommentFactory(author=UserFactory(), project=project)
        self.client.force_authenticate(UserFactory())
        response = self.client.get(
            reverse("Comment-list", kwargs={"project_id": project.id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_no_permission(self):
        organization = OrganizationFactory()
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        organization.projects.add(project)
        comment = CommentFactory(author=UserFactory(), project=project)
        payload = {
            "content": "NewContent",
            "project_id": comment.project_id,
        }
        self.client.force_authenticate(UserFactory())
        response = self.client.put(
            reverse(
                "Comment-detail", kwargs={"id": comment.id, "project_id": project.id}
            ),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_partial_update_no_permission(self):
        organization = OrganizationFactory()
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        organization.projects.add(project)
        comment = CommentFactory(author=UserFactory(), project=project)
        payload = {"content": "NewContent"}
        self.client.force_authenticate(UserFactory())
        response = self.client.patch(
            reverse(
                "Comment-detail", kwargs={"id": comment.id, "project_id": project.id}
            ),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_destroy_no_permission(self):
        organization = OrganizationFactory()
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        organization.projects.add(project)
        comment = CommentFactory(author=UserFactory(), project=project)
        self.client.force_authenticate(UserFactory())
        response = self.client.delete(
            reverse(
                "Comment-detail", kwargs={"id": comment.id, "project_id": project.id}
            )
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class CommentTestCaseOwner(JwtAPITestCase):
    def test_retrieve_owner(self):
        organization = OrganizationFactory()
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        organization.projects.add(project)
        comment = CommentFactory(author=UserFactory(), project=project)
        self.client.force_authenticate(comment.author)
        response = self.client.get(
            reverse(
                "Comment-detail", kwargs={"id": comment.id, "project_id": project.id}
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

    def test_list_owner(self):
        organization = OrganizationFactory()
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        organization.projects.add(project)
        comment = CommentFactory(author=UserFactory(), project=project)
        self.client.force_authenticate(comment.author)
        response = self.client.get(
            reverse("Comment-list", kwargs={"project_id": project.id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

    def test_update_owner(self):
        organization = OrganizationFactory()
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        organization.projects.add(project)
        comment = CommentFactory(author=UserFactory(), project=project)
        payload = {
            "content": "NewContent",
            "project_id": comment.project_id,
        }
        self.client.force_authenticate(comment.author)
        response = self.client.put(
            reverse(
                "Comment-detail", kwargs={"id": comment.id, "project_id": project.id}
            ),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_partial_update_owner(self):
        organization = OrganizationFactory()
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        organization.projects.add(project)
        comment = CommentFactory(author=UserFactory(), project=project)
        payload = {"content": "NewContent"}
        self.client.force_authenticate(comment.author)
        response = self.client.patch(
            reverse(
                "Comment-detail", kwargs={"id": comment.id, "project_id": project.id}
            ),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_destroy_owner(self):
        organization = OrganizationFactory()
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        organization.projects.add(project)
        comment = CommentFactory(author=UserFactory(), project=project)
        self.client.force_authenticate(comment.author)
        response = self.client.delete(
            reverse(
                "Comment-detail", kwargs={"id": comment.id, "project_id": project.id}
            )
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class CommentTestCaseBasePermission(JwtAPITestCase):
    def test_update_base_permission(self):
        organization = OrganizationFactory()
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        organization.projects.add(project)
        comment = CommentFactory(author=UserFactory(), project=project)
        payload = {
            "content": "NewContent",
            "project_id": comment.project_id,
        }
        user = UserFactory(permissions=[("feedbacks.change_comment", None)])
        self.client.force_authenticate(user)
        response = self.client.put(
            reverse(
                "Comment-detail", kwargs={"id": comment.id, "project_id": project.id}
            ),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        comment.refresh_from_db()
        self.assertEqual(comment.content, "NewContent")
        payload["content"] = self.get_base64_image()
        response = self.client.put(
            reverse(
                "Comment-detail", kwargs={"id": comment.id, "project_id": project.id}
            ),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        comment = Comment.objects.get(id=response.json()["id"])
        self.assertEqual(comment.images.count(), 1)

    def test_partial_update_base_permission(self):
        organization = OrganizationFactory()
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        organization.projects.add(project)
        comment = CommentFactory(author=UserFactory(), project=project)
        payload = {"content": "NewContent"}
        user = UserFactory(permissions=[("feedbacks.change_comment", None)])
        self.client.force_authenticate(user)
        response = self.client.patch(
            reverse(
                "Comment-detail", kwargs={"id": comment.id, "project_id": project.id}
            ),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        comment.refresh_from_db()
        self.assertEqual(comment.content, "NewContent")
        payload["content"] = self.get_base64_image()
        response = self.client.patch(
            reverse(
                "Comment-detail", kwargs={"id": comment.id, "project_id": project.id}
            ),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        comment = Comment.objects.get(id=response.json()["id"])
        self.assertEqual(comment.images.count(), 1)

    def test_destroy_base_permission(self):
        organization = OrganizationFactory()
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        organization.projects.add(project)
        comment = CommentFactory(author=UserFactory(), project=project)
        user = UserFactory(permissions=[("feedbacks.delete_comment", None)])
        self.client.force_authenticate(user)
        response = self.client.delete(
            reverse(
                "Comment-detail", kwargs={"id": comment.id, "project_id": project.id}
            )
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class CommentTestCaseProjectPermission(JwtAPITestCase):
    def test_create_project_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.ORG)
        user = UserFactory(permissions=[("projects.view_project", project)])
        payload = {
            "project_id": project.id,
            "content": FAKER.sentence(),
        }
        self.client.force_authenticate(user)
        response = self.client.post(
            reverse("Comment-list", kwargs={"project_id": project.id}), data=payload
        )
        self.assertEqual(
            response.status_code, status.HTTP_201_CREATED, response.content
        )
        content = response.json()
        user_data = {
            "id": user.id,
            "keycloak_id": user.keycloak_id,
            "people_id": user.people_id,
            "email": user.email,
            "given_name": user.given_name,
            "family_name": user.family_name,
            "pronouns": user.pronouns,
            "job": user.job,
            "profile_picture": None,
        }
        self.assertEqual(content["author"], user_data)
        self.assertEqual(content["content"], payload["content"])
        payload["content"] = self.get_base64_image()
        response = self.client.post(
            reverse("Comment-list", kwargs={"project_id": project.id}), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.json())
        comment = Comment.objects.get(id=response.json()["id"])
        self.assertEqual(comment.images.count(), 1)

    def test_update_project_permission(self):
        organization = OrganizationFactory()
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        organization.projects.add(project)
        comment = CommentFactory(author=UserFactory(), project=project)
        payload = {
            "content": "NewContent",
            "project_id": comment.project_id,
        }
        user = UserFactory(permissions=[("projects.change_comment", project)])
        self.client.force_authenticate(user)
        response = self.client.put(
            reverse(
                "Comment-detail", kwargs={"id": comment.id, "project_id": project.id}
            ),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        comment.refresh_from_db()
        self.assertEqual(comment.content, "NewContent")
        payload["content"] = self.get_base64_image()
        response = self.client.put(
            reverse(
                "Comment-detail", kwargs={"id": comment.id, "project_id": project.id}
            ),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        comment = Comment.objects.get(id=response.json()["id"])
        self.assertEqual(comment.images.count(), 1)

    def test_partial_update_project_permission(self):
        organization = OrganizationFactory()
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        organization.projects.add(project)
        comment = CommentFactory(author=UserFactory(), project=project)
        payload = {"content": "NewContent"}
        user = UserFactory(permissions=[("projects.change_comment", project)])
        self.client.force_authenticate(user)
        response = self.client.patch(
            reverse(
                "Comment-detail", kwargs={"id": comment.id, "project_id": project.id}
            ),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        comment.refresh_from_db()
        self.assertEqual(comment.content, "NewContent")
        payload["content"] = self.get_base64_image()
        response = self.client.patch(
            reverse(
                "Comment-detail", kwargs={"id": comment.id, "project_id": project.id}
            ),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        comment = Comment.objects.get(id=response.json()["id"])
        self.assertEqual(comment.images.count(), 1)

    def test_destroy_project_permission(self):
        organization = OrganizationFactory()
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        organization.projects.add(project)
        comment = CommentFactory(author=UserFactory(), project=project)
        user = UserFactory(permissions=[("projects.delete_comment", project)])
        self.client.force_authenticate(user)
        response = self.client.delete(
            reverse(
                "Comment-detail", kwargs={"id": comment.id, "project_id": project.id}
            )
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class CommentTestCaseOrganizationPermission(JwtAPITestCase):
    def test_create_org_permission(self):
        organization = OrganizationFactory()
        user = UserFactory(
            permissions=[("organizations.view_org_project", organization)]
        )
        project = ProjectFactory(publication_status=Project.PublicationStatus.ORG)
        project.organizations.add(organization)
        payload = {
            "project_id": project.id,
            "content": FAKER.sentence(),
        }
        self.client.force_authenticate(user)
        response = self.client.post(
            reverse("Comment-list", kwargs={"project_id": project.id}), data=payload
        )
        self.assertEqual(
            response.status_code, status.HTTP_201_CREATED, response.content
        )
        content = response.json()
        user_data = {
            "id": user.id,
            "keycloak_id": user.keycloak_id,
            "people_id": user.people_id,
            "email": user.email,
            "given_name": user.given_name,
            "family_name": user.family_name,
            "pronouns": user.pronouns,
            "job": user.job,
            "profile_picture": None,
        }
        self.assertEqual(content["author"], user_data)
        self.assertEqual(content["content"], payload["content"])
        payload["content"] = self.get_base64_image()
        response = self.client.post(
            reverse("Comment-list", kwargs={"project_id": project.id}), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.json())
        comment = Comment.objects.get(id=response.json()["id"])
        self.assertEqual(comment.images.count(), 1)

    def test_update_org_permission(self):
        organization = OrganizationFactory()
        user = UserFactory(permissions=[("organizations.change_comment", organization)])
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        project.organizations.add(organization)
        organization.projects.add(project)
        comment = CommentFactory(author=UserFactory(), project=project)
        payload = {
            "content": "NewContent",
            "project_id": comment.project_id,
        }
        self.client.force_authenticate(user)
        response = self.client.put(
            reverse(
                "Comment-detail", kwargs={"id": comment.id, "project_id": project.id}
            ),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        comment.refresh_from_db()
        self.assertEqual(comment.content, "NewContent")
        payload["content"] = self.get_base64_image()
        response = self.client.put(
            reverse(
                "Comment-detail", kwargs={"id": comment.id, "project_id": project.id}
            ),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        comment = Comment.objects.get(id=response.json()["id"])
        self.assertEqual(comment.images.count(), 1)

    def test_partial_update_org_permission(self):
        organization = OrganizationFactory()
        user = UserFactory(permissions=[("organizations.change_comment", organization)])
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        project.organizations.add(organization)
        organization.projects.add(project)
        comment = CommentFactory(author=UserFactory(), project=project)
        payload = {"content": "NewContent"}
        self.client.force_authenticate(user)
        response = self.client.patch(
            reverse(
                "Comment-detail", kwargs={"id": comment.id, "project_id": project.id}
            ),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        comment.refresh_from_db()
        self.assertEqual(comment.content, "NewContent")
        payload["content"] = self.get_base64_image()
        response = self.client.patch(
            reverse(
                "Comment-detail", kwargs={"id": comment.id, "project_id": project.id}
            ),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        comment = Comment.objects.get(id=response.json()["id"])
        self.assertEqual(comment.images.count(), 1)

    def test_destroy_org_permission(self):
        organization = OrganizationFactory()
        user = UserFactory(permissions=[("organizations.delete_comment", organization)])
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        project.organizations.add(organization)
        organization.projects.add(project)
        comment = CommentFactory(author=UserFactory(), project=project)
        self.client.force_authenticate(user)
        response = self.client.delete(
            reverse(
                "Comment-detail", kwargs={"id": comment.id, "project_id": project.id}
            )
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class OtherCommentTestCase(JwtAPITestCase):
    def test_filter_by_project_and_hierarchy(self):
        project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
        )
        other_project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
        )
        comments = CommentFactory.create_batch(3, project=project)
        other_comments = CommentFactory.create_batch(3, project=other_project)
        subcomments = defaultdict(set)
        for comment in comments:
            for _ in range(3):
                subcomments[comment.id].add(
                    CommentFactory(project=project, reply_on=comment).id
                )
        for other_comment in other_comments:
            CommentFactory.create_batch(
                3, project=other_project, reply_on=other_comment
            )

        self.client.force_authenticate(UserFactory())
        response = self.client.get(
            reverse("Comment-list", kwargs={"project_id": project.id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

        content = response.json()
        self.assertEqual(content["count"], 3)
        for i in range(3):
            self.assertEqual(
                {r["id"] for r in content["results"][i]["replies"]},
                subcomments[content["results"][i]["id"]],
            )

    def test_can_delete_reply(self):
        organization = OrganizationFactory()
        user = UserFactory()
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        project.organizations.add(organization)
        project.members.add(user)
        comment = CommentFactory(project=project)
        reply = CommentFactory(project=project, reply_on=comment, author=user)

        organization.users.add(user)
        self.client.force_authenticate(user)
        response = self.client.delete(
            reverse("Comment-detail", kwargs={"id": reply.id, "project_id": project.id})
        )
        self.assertEqual(
            response.status_code, status.HTTP_204_NO_CONTENT, response.content
        )

    def test_can_patch_reply(self):
        organization = OrganizationFactory()
        user = UserFactory()
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        project.organizations.add(organization)
        project.members.add(user)
        comment = CommentFactory(project=project)
        reply = CommentFactory(project=project, reply_on=comment, author=user)

        payload = {
            "content": "NewContent",
            "project_id": reply.project_id,
            "reply_on_id": reply.reply_on_id,
        }
        organization.users.add(user)
        self.client.force_authenticate(user)
        kwargs = {"id": reply.id, "project_id": project.id}
        response = self.client.patch(
            reverse("Comment-detail", kwargs=kwargs), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

        reply.refresh_from_db()
        self.assertEqual(reply.content, "NewContent")

    def test_no_content_from_deleted_comment(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        user = UserFactory()
        comment = CommentFactory.create(project=project)
        subcomments = []
        for _ in range(3):
            subcomments.append(CommentFactory(project=project, reply_on=comment))
        comment.soft_delete(user)

        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("Comment-list", kwargs={"project_id": project.id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["id"], comment.id)
        self.assertEqual(content["results"][0]["content"], "<deleted comment>")

        replies = content["results"][0]["replies"]
        self.assertEqual({r["id"] for r in replies}, {r.id for r in subcomments})
        self.assertEqual(
            {r["content"] for r in replies}, {r.content for r in subcomments}
        )

    def test_cannot_reply_to_themselves(self):
        organization = OrganizationFactory()
        user = UserFactory()
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        project.organizations.add(organization)
        project.members.add(user)
        comment = CommentFactory(author=user, project=project)

        payload = {"reply_on_id": comment.id}
        organization.users.add(user)
        self.client.force_authenticate(user)
        kwargs = {"id": comment.id, "project_id": project.id}
        response = self.client.patch(
            reverse("Comment-detail", kwargs=kwargs), data=payload
        )
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.content
        )

    def test_cannot_reply_to_reply(self):
        user = UserFactory()
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        comment = CommentFactory(project=project)
        reply = CommentFactory(project=project, reply_on=comment, author=user)

        payload = {
            "content": "Content",
            "project_id": project.id,
            "reply_on_id": reply.id,
        }
        self.client.force_authenticate(user)
        response = self.client.post(
            reverse("Comment-list", kwargs={"project_id": project.id}), data=payload
        )
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.content
        )

    def test_only_deleted_with_replies_returned(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        user = UserFactory()
        with_replies = CommentFactory.create(project=project)
        without_replies = CommentFactory.create(project=project)
        CommentFactory(project=project, reply_on=with_replies)
        with_replies.soft_delete(user)
        without_replies.soft_delete(user)

        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("Comment-list", kwargs={"project_id": project.id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

        content = response.json()
        self.assertEqual(content["count"], 1)
        self.assertEqual(content["results"][0]["id"], with_replies.id)
        self.assertEqual(content["results"][0]["content"], "<deleted comment>")
