from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from faker import Faker
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.accounts.utils import get_superadmins_group
from apps.analytics.factories import StatFactory
from apps.commons.test import JwtAPITestCase
from apps.goals.models import Goal

faker = Faker()


class StatsTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.stat = StatFactory()
        cls.project = cls.stat.project
        cls.superadmin = UserFactory(groups=[get_superadmins_group()])

    def test_comment_stats(self):
        self.client.force_authenticate(self.superadmin)

        # Create a comment
        payload = {
            "project_id": self.project.id,
            "content": faker.text(),
        }
        response = self.client.post(
            reverse("Comment-list", args=(self.project.id,)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        comment_id = response.json()["id"]
        self.stat.refresh_from_db()
        self.assertEqual(self.stat.comments, 1)

        # Create a reply
        payload = {
            "project_id": self.project.id,
            "content": faker.text(),
            "reply_on_id": comment_id,
        }
        response = self.client.post(
            reverse("Comment-list", args=(self.project.id,)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        reply_id = response.json()["id"]
        self.stat.refresh_from_db()
        self.assertEqual(self.stat.replies, 1)

        # Delete the reply
        response = self.client.delete(
            reverse("Comment-detail", args=(self.project.id, reply_id))
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.stat.refresh_from_db()
        self.assertEqual(self.stat.replies, 0)

        # Delete the comment
        response = self.client.delete(
            reverse("Comment-detail", args=(self.project.id, comment_id))
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.stat.refresh_from_db()
        self.assertEqual(self.stat.comments, 0)

    def test_follow_stats(self):
        self.client.force_authenticate(self.superadmin)

        # Create a follow
        payload = {"project_id": self.project.id}
        response = self.client.post(
            reverse("Followed-list", args=(self.project.id,)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        follow_id = response.json()["id"]
        self.stat.refresh_from_db()
        self.assertEqual(self.stat.follows, 1)

        # Delete the follow
        response = self.client.delete(
            reverse("Followed-detail", args=(self.project.id, follow_id))
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.stat.refresh_from_db()
        self.assertEqual(self.stat.follows, 0)

    def test_link_stats(self):
        self.client.force_authenticate(self.superadmin)

        # Create a link
        payload = {
            "project_id": self.project.id,
            "site_url": faker.url(),
        }
        response = self.client.post(
            reverse("AttachmentLink-list", args=(self.project.id,)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        link_id = response.json()["id"]
        self.stat.refresh_from_db()
        self.assertEqual(self.stat.links, 1)

        # Delete the link
        response = self.client.delete(
            reverse("AttachmentLink-detail", args=(self.project.id, link_id))
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.stat.refresh_from_db()
        self.assertEqual(self.stat.links, 0)

    def test_file_stats(self):
        self.client.force_authenticate(self.superadmin)

        # Create a file
        payload = {
            "project_id": self.project.id,
            "title": faker.word(),
            "file": SimpleUploadedFile(
                "test_attachment_file.txt",
                b"test attachment file",
                content_type="text/plain",
            ),
            "mime": "text/plain",
        }
        response = self.client.post(
            reverse("AttachmentFile-list", args=(self.project.id,)),
            data=payload,
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        file_id = response.json()["id"]
        self.stat.refresh_from_db()
        self.assertEqual(self.stat.files, 1)

        # Delete the file
        response = self.client.delete(
            reverse("AttachmentFile-detail", args=(self.project.id, file_id))
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.stat.refresh_from_db()
        self.assertEqual(self.stat.files, 0)

    def test_blog_entry_stats(self):
        self.client.force_authenticate(self.superadmin)

        # Create a blog entry
        payload = {
            "project_id": self.project.id,
            "title": faker.word(),
            "content": faker.text(),
        }
        response = self.client.post(
            reverse("BlogEntry-list", args=(self.project.id,)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        blog_entry_id = response.json()["id"]
        self.stat.refresh_from_db()
        self.assertEqual(self.stat.blog_entries, 1)

        # Delete the blog entry
        response = self.client.delete(
            reverse("BlogEntry-detail", args=(self.project.id, blog_entry_id))
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.stat.refresh_from_db()
        self.assertEqual(self.stat.blog_entries, 0)

    def test_goal_stats(self):
        self.client.force_authenticate(self.superadmin)

        # Create a goal
        payload = {
            "project_id": self.project.id,
            "title": faker.word(),
            "status": Goal.GoalStatus.ONGOING,
        }
        response = self.client.post(
            reverse("Goal-list", args=(self.project.id,)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        goal_id = response.json()["id"]
        self.stat.refresh_from_db()
        self.assertEqual(self.stat.goals, 1)

        # Delete the goal
        response = self.client.delete(
            reverse("Goal-detail", args=(self.project.id, goal_id))
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.stat.refresh_from_db()
        self.assertEqual(self.stat.goals, 0)

    def test_update_project_description(self):
        self.client.force_authenticate(self.superadmin)

        payload = {"description": faker.word()}
        response = self.client.patch(
            reverse("Project-detail", args=(self.project.id,)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.stat.refresh_from_db()
        self.assertEqual(self.stat.description_length, len(payload["description"]))
