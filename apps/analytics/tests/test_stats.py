from io import StringIO
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.urls import reverse
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.analytics.factories import StatFactory
from apps.analytics.models import Stat
from apps.commons.test import JwtAPITestCase
from apps.feedbacks.factories import CommentFactory, FollowFactory
from apps.files.factories import AttachmentFileFactory, AttachmentLinkFactory
from apps.files.models import AttachmentType
from apps.files.tests.views.mock_response import MockResponse
from apps.goals.factories import GoalFactory
from apps.goals.models import Goal
from apps.projects.factories import BlogEntryFactory, ProjectFactory


class StatsTestCase(JwtAPITestCase):
    @staticmethod
    def call_command(shortid=None):
        out = StringIO()
        call_command(
            "update_stats",
            shortid=shortid,
            stdout=out,
            stderr=StringIO(),
        )
        return out.getvalue()

    def test_run_command(self):
        project = ProjectFactory()
        comments = CommentFactory.create_batch(3, project=project)
        CommentFactory.create_batch(3, project=project, reply_on=comments[0])
        FollowFactory.create_batch(3, project=project)
        AttachmentLinkFactory.create_batch(3, project=project)
        AttachmentFileFactory.create_batch(3, project=project)
        BlogEntryFactory.create_batch(3, project=project)
        GoalFactory.create_batch(3, project=project)
        self.call_command()
        project.refresh_from_db()
        self.assertEqual(project.stat.comments, 3)
        self.assertEqual(project.stat.replies, 3)
        self.assertEqual(project.stat.follows, 3)
        self.assertEqual(project.stat.links, 3)
        self.assertEqual(project.stat.files, 3)
        self.assertEqual(project.stat.blog_entries, 3)
        self.assertEqual(project.stat.goals, 3)

    def test_run_command_with_arg(self):
        project = ProjectFactory()
        comments = CommentFactory.create_batch(3, project=project)
        CommentFactory.create_batch(3, project=project, reply_on=comments[0])
        FollowFactory.create_batch(3, project=project)
        AttachmentLinkFactory.create_batch(3, project=project)
        AttachmentFileFactory.create_batch(3, project=project)
        BlogEntryFactory.create_batch(3, project=project)
        GoalFactory.create_batch(3, project=project)
        project2 = ProjectFactory()
        comments2 = CommentFactory.create_batch(3, project=project2)
        CommentFactory.create_batch(3, project=project2, reply_on=comments2[0])
        FollowFactory.create_batch(3, project=project2)
        AttachmentLinkFactory.create_batch(3, project=project2)
        AttachmentFileFactory.create_batch(3, project=project2)
        BlogEntryFactory.create_batch(3, project=project2)
        GoalFactory.create_batch(3, project=project2)
        self.call_command(shortid=project.id)
        project.refresh_from_db()
        project2.refresh_from_db()
        self.assertEqual(project.stat.comments, 3)
        self.assertEqual(project.stat.replies, 3)
        self.assertEqual(project.stat.follows, 3)
        self.assertEqual(project.stat.links, 3)
        self.assertEqual(project.stat.files, 3)
        self.assertEqual(project.stat.blog_entries, 3)
        self.assertEqual(project.stat.goals, 3)
        self.assertIsNone(Stat.objects.filter(project=project2).first())

    def test_post_comment(self):
        stat = StatFactory()
        payload = {
            "project_id": stat.project.id,
            "content": "",
        }
        self.client.force_authenticate(
            UserFactory(permissions=[("feedbacks.add_comment", None)])
        )
        response = self.client.post(
            reverse("Comment-list", kwargs={"project_id": stat.project.id}),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        stat.refresh_from_db()
        self.assertEqual(stat.comments, 1)

    def test_delete_comment(self):
        stat = StatFactory()
        comment = CommentFactory(project=stat.project, author=UserFactory())
        comment.save()
        self.client.force_authenticate(
            UserFactory(permissions=[("feedbacks.delete_comment", None)])
        )
        response = self.client.delete(
            reverse(
                "Comment-detail",
                kwargs={"project_id": stat.project.id, "id": comment.id},
            )
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        stat.refresh_from_db()
        self.assertEqual(stat.comments, 0)

    def test_post_reply(self):
        stat = StatFactory()
        user = UserFactory(permissions=[("feedbacks.add_comment", None)])
        main = CommentFactory(author=user, project=stat.project)
        main.save()
        payload = {
            "project_id": stat.project.id,
            "content": "",
            "reply_on_id": main.id,
        }
        self.client.force_authenticate(user)
        response = self.client.post(
            reverse("Comment-list", kwargs={"project_id": stat.project.id}),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        stat.refresh_from_db()
        self.assertEqual(stat.replies, 1)

    def test_delete_reply(self):
        stat = StatFactory()
        main = CommentFactory(project=stat.project, author=UserFactory())
        reply = CommentFactory(
            project=stat.project, author=UserFactory(), reply_on=main
        )
        self.client.force_authenticate(
            UserFactory(permissions=[("feedbacks.delete_comment", None)])
        )
        response = self.client.delete(
            reverse(
                "Comment-detail", kwargs={"project_id": stat.project.id, "id": reply.id}
            )
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        stat.refresh_from_db()
        self.assertEqual(stat.replies, 0)

    def test_post_follow(self):
        stat = StatFactory()
        payload = {"project_id": stat.project.id}
        self.client.force_authenticate(
            UserFactory(permissions=[("feedbacks.add_follow", None)])
        )
        response = self.client.post(
            reverse("Followed-list", kwargs={"project_id": stat.project.id}),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        stat.refresh_from_db()
        self.assertEqual(stat.follows, 1)

    def test_delete_follow(self):
        stat = StatFactory()
        follow = FollowFactory(project=stat.project, follower=UserFactory())
        follow.save()
        self.client.force_authenticate(
            UserFactory(permissions=[("feedbacks.delete_follow", None)])
        )
        response = self.client.delete(
            reverse(
                "Followed-detail",
                kwargs={"project_id": stat.project.id, "id": follow.id},
            )
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        stat.refresh_from_db()
        self.assertEqual(stat.follows, 0)

    @patch(target="requests.get", return_value=MockResponse())
    def test_post_link(self, mocked):
        stat = StatFactory()
        payload = {"site_url": "https://google.com", "project_id": stat.project.id}
        self.client.force_authenticate(
            UserFactory(permissions=[("projects.change_project", None)])
        )
        response = self.client.post(
            reverse("AttachmentLink-list", kwargs={"project_id": stat.project.id}),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        stat.refresh_from_db()
        self.assertEqual(stat.links, 1)

    def test_delete_link(self):
        stat = StatFactory()
        link = AttachmentLinkFactory(project=stat.project)
        link.save()
        self.client.force_authenticate(
            UserFactory(permissions=[("projects.change_project", None)])
        )
        response = self.client.delete(
            reverse(
                "AttachmentLink-detail",
                kwargs={"project_id": stat.project.id, "id": link.id},
            )
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        stat.refresh_from_db()
        self.assertEqual(stat.links, 0)

    def test_post_file(self):
        stat = StatFactory()
        payload = {
            "mime": "mime",
            "title": "title",
            "file": SimpleUploadedFile(
                "test_attachment_file.txt",
                b"test attachment file",
                content_type="text/plain",
            ),
            "attachment_type": AttachmentType.FILE,
            "project_id": stat.project.id,
        }
        self.client.force_authenticate(
            UserFactory(permissions=[("projects.change_project", None)])
        )
        response = self.client.post(
            reverse("AttachmentFile-list", kwargs={"project_id": stat.project.id}),
            data=payload,
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        stat.refresh_from_db()
        self.assertEqual(stat.files, 1)

    def test_delete_file(self):
        stat = StatFactory()
        file = AttachmentFileFactory(project=stat.project)
        file.save()
        self.client.force_authenticate(
            UserFactory(permissions=[("projects.change_project", None)])
        )
        response = self.client.delete(
            reverse(
                "AttachmentFile-detail",
                kwargs={"project_id": stat.project.id, "id": file.id},
            )
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        stat.refresh_from_db()
        self.assertEqual(stat.files, 0)

    def test_post_blog_entry(self):
        stat = StatFactory()
        payload = {
            "title": "title",
            "content": "content",
            "project_id": stat.project.id,
        }
        self.client.force_authenticate(
            UserFactory(permissions=[("projects.change_project", None)])
        )
        response = self.client.post(
            reverse("BlogEntry-list", kwargs={"project_id": stat.project.id}),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        stat.refresh_from_db()
        self.assertEqual(stat.blog_entries, 1)

    def test_delete_blog_entry(self):
        stat = StatFactory()
        blog_entry = BlogEntryFactory(project=stat.project)
        blog_entry.save()
        self.client.force_authenticate(
            UserFactory(permissions=[("projects.change_project", None)])
        )
        response = self.client.delete(
            reverse(
                "BlogEntry-detail",
                kwargs={"project_id": stat.project.id, "id": blog_entry.id},
            )
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        stat.refresh_from_db()
        self.assertEqual(stat.blog_entries, 0)

    def test_post_goal(self):
        stat = StatFactory()
        payload = {
            "title": "title",
            "status": Goal.GoalStatus.ONGOING,
            "project_id": stat.project.id,
        }
        self.client.force_authenticate(
            UserFactory(permissions=[("projects.change_project", None)])
        )
        response = self.client.post(
            reverse("Goal-list", kwargs={"project_id": stat.project.id}), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        stat.refresh_from_db()
        self.assertEqual(stat.goals, 1)

    def test_delete_goal(self):
        stat = StatFactory()
        goal = GoalFactory(project=stat.project)
        goal.save()
        self.client.force_authenticate(
            UserFactory(permissions=[("projects.change_project", None)])
        )
        response = self.client.delete(
            reverse(
                "Goal-detail", kwargs={"project_id": stat.project.id, "id": goal.id}
            )
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        stat.refresh_from_db()
        self.assertEqual(stat.goals, 0)

    def test_versions(self):
        stat = StatFactory()
        initial = stat.project.archive.count()
        self.client.force_authenticate(
            UserFactory(permissions=[("projects.change_project", None)])
        )
        payload = {"title": "NewTitle1"}
        response = self.client.patch(
            reverse("Project-detail", kwargs={"id": stat.project.id}), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        stat.refresh_from_db()
        self.assertEqual(stat.versions, initial + 1)
        payload = {"title": "NewTitle2"}
        response = self.client.patch(
            reverse("Project-detail", kwargs={"id": stat.project.id}), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        stat.refresh_from_db()
        self.assertEqual(stat.versions, initial + 2)
        payload = {"title": "NewTitle3"}
        response = self.client.patch(
            reverse("Project-detail", kwargs={"id": stat.project.id}), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        stat.refresh_from_db()
        self.assertEqual(stat.versions, initial + 3)

    def test_update_project_description(self):
        self.client.force_authenticate(
            UserFactory(permissions=[("projects.change_project", None)])
        )
        stat = StatFactory()
        payload = {"description": "ABCDE"}
        response = self.client.patch(
            reverse("Project-detail", kwargs={"id": stat.project.id}), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        stat.refresh_from_db()
        self.assertEqual(stat.description_length, 5)
        payload = {"description": "ABCDEFGHIJ"}
        response = self.client.patch(
            reverse("Project-detail", kwargs={"id": stat.project.id}), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        stat.refresh_from_db()
        self.assertEqual(stat.description_length, 10)

    def test_update_project_not_description(self):
        self.client.force_authenticate(
            UserFactory(permissions=[("projects.change_project", None)])
        )
        stat = StatFactory()
        payload = {"title": "title"}
        response = self.client.patch(
            reverse("Project-detail", kwargs={"id": stat.project.id}), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        stat.refresh_from_db()
        self.assertEqual(stat.description_length, 0)
