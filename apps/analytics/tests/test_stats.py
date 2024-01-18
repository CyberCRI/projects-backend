from io import StringIO
from unittest.mock import patch
from faker import Faker

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.urls import reverse
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.accounts.utils import get_superadmins_group
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
        assert response.status_code == status.HTTP_201_CREATED
        comment_id = response.json()["id"]
        self.stat.refresh_from_db()
        assert self.stat.comments == 1

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
        assert response.status_code == status.HTTP_201_CREATED
        reply_id = response.json()["id"]
        self.stat.refresh_from_db()
        assert self.stat.replies == 1

        # Delete the reply
        response = self.client.delete(
            reverse("Comment-detail", args=(self.project.id, reply_id))
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        self.stat.refresh_from_db()
        assert self.stat.replies == 0

        # Delete the comment
        response = self.client.delete(
            reverse("Comment-detail", args=(self.project.id, comment_id))
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        self.stat.refresh_from_db()
        assert self.stat.comments == 0

    def test_follow_stats(self):
        self.client.force_authenticate(self.superadmin)        

        # Create a follow
        payload = {
            "project_id": self.project.id
        }
        response = self.client.post(
            reverse("Followed-list", args=(self.project.id,)),
            data=payload,
        )
        assert response.status_code == status.HTTP_201_CREATED
        follow_id = response.json()["id"]
        self.stat.refresh_from_db()
        assert self.stat.follows == 1

        # Delete the follow
        response = self.client.delete(
            reverse("Followed-detail", args=(self.project.id, follow_id))
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        self.stat.refresh_from_db()
        assert self.stat.follows == 0
    
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
        assert response.status_code == status.HTTP_201_CREATED
        link_id = response.json()["id"]
        self.stat.refresh_from_db()
        assert self.stat.links == 1

        # Delete the link
        response = self.client.delete(
            reverse("AttachmentLink-detail", args=(self.project.id, link_id))
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        self.stat.refresh_from_db()
        assert self.stat.links == 0

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
            "attachment_type": AttachmentType.FILE,
        }
        response = self.client.post(
            reverse("AttachmentFile-list", args=(self.project.id,)),
            data=payload,
            format="multipart",
        )
        print(response.status_code, response.json())
        assert response.status_code == status.HTTP_201_CREATED
        file_id = response.json()["id"]
        self.stat.refresh_from_db()
        assert self.stat.files == 1

        # Delete the file
        response = self.client.delete(
            reverse("AttachmentFile-detail", args=(self.project.id, file_id))
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        self.stat.refresh_from_db()
        assert self.stat.files == 0

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
        assert response.status_code == status.HTTP_201_CREATED
        blog_entry_id = response.json()["id"]
        self.stat.refresh_from_db()
        assert self.stat.blog_entries == 1

        # Delete the blog entry
        response = self.client.delete(
            reverse("BlogEntry-detail", args=(self.project.id, blog_entry_id))
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        self.stat.refresh_from_db()
        assert self.stat.blog_entries == 0

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
        assert response.status_code == status.HTTP_201_CREATED
        goal_id = response.json()["id"]
        self.stat.refresh_from_db()
        assert self.stat.goals == 1

        # Delete the goal
        response = self.client.delete(
            reverse("Goal-detail", args=(self.project.id, goal_id))
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        self.stat.refresh_from_db()
        assert self.stat.goals == 0

    def test_update_project_description(self):
        self.client.force_authenticate(self.superadmin)
        
        payload = {
            "description": faker.word()
        }
        response = self.client.patch(
            reverse("Project-detail", args=(self.project.id,)),
            data=payload,
        )
        assert response.status_code == status.HTTP_200_OK
        self.stat.refresh_from_db()
        assert self.stat.description_length == len(payload["description"])
