from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from faker import Faker
from parameterized import parameterized
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.announcements.factories import AnnouncementFactory
from apps.announcements.models import Announcement
from apps.commons.test import JwtAPITestCase, TestRoles
from apps.files.enums import AttachmentType
from apps.files.factories import AttachmentFileFactory, AttachmentLinkFactory
from apps.files.tests.views.mock_response import MockResponse
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import (
    BlogEntryFactory,
    GoalFactory,
    LinkedProjectFactory,
    LocationFactory,
    ProjectFactory,
)
from apps.projects.models import Goal, Location

faker = Faker()


class UpdateLockedProjectTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.project = ProjectFactory(is_locked=True, organizations=[cls.organization])
        cls.user = UserFactory(groups=[cls.project.get_owners()])

        cls.linked_project = LinkedProjectFactory(
            target=cls.project, project=ProjectFactory(organizations=[cls.organization])
        )
        cls.blog_entry = BlogEntryFactory(project=cls.project)
        cls.goal = GoalFactory(project=cls.project)
        cls.location = LocationFactory(project=cls.project)
        cls.attachment_file = AttachmentFileFactory(project=cls.project)
        cls.attachment_link = AttachmentLinkFactory(project=cls.project)
        cls.announcement = AnnouncementFactory(project=cls.project)

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_ADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_FACILITATOR, status.HTTP_200_OK),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_MEMBER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_OWNER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_REVIEWER, status.HTTP_200_OK),
        ]
    )
    def test_update_locked_project(self, role, expected_code):
        user = self.get_parameterized_test_user(role, instances=[self.project])
        self.client.force_authenticate(user)
        payload = {
            "title": faker.sentence(),
        }
        response = self.client.patch(
            reverse("Project-detail", args=(self.project.id,)),
            data=payload,
        )
        self.assertEqual(response.status_code, expected_code)

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_ADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_FACILITATOR, status.HTTP_200_OK),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_MEMBER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_OWNER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_REVIEWER, status.HTTP_200_OK),
        ]
    )
    def test_destroy_locked_project(self, role, expected_code):
        project = ProjectFactory(is_locked=True, organizations=[self.organization])
        user = self.get_parameterized_test_user(role, instances=[project])
        self.client.force_authenticate(user)
        payload = {
            "title": faker.sentence(),
        }
        response = self.client.patch(
            reverse("Project-detail", args=(project.id,)),
            data=payload,
        )
        self.assertEqual(response.status_code, expected_code)

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_ADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_FACILITATOR, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_MEMBER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_OWNER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_REVIEWER, status.HTTP_204_NO_CONTENT),
        ]
    )
    def test_add_member_to_locked_project(self, role, expected_code):
        user = self.get_parameterized_test_user(role, instances=[self.project])
        self.client.force_authenticate(user)
        payload = {
            "members": [],
        }
        response = self.client.post(
            reverse("Project-add-member", args=(self.project.id,)),
            data=payload,
        )
        self.assertEqual(response.status_code, expected_code)

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_ADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_FACILITATOR, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_MEMBER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_OWNER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_REVIEWER, status.HTTP_204_NO_CONTENT),
        ]
    )
    def test_remove_member_from_locked_project(self, role, expected_code):
        user = self.get_parameterized_test_user(role, instances=[self.project])
        self.client.force_authenticate(user)
        payload = {
            "users": [],
        }
        response = self.client.post(
            reverse("Project-remove-member", args=(self.project.id,)),
            data=payload,
        )
        self.assertEqual(response.status_code, expected_code)

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_201_CREATED),
            (TestRoles.ORG_ADMIN, status.HTTP_201_CREATED),
            (TestRoles.ORG_FACILITATOR, status.HTTP_201_CREATED),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_MEMBER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_OWNER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_REVIEWER, status.HTTP_201_CREATED),
        ]
    )
    @patch("apps.files.serializers.AttachmentLinkSerializer.get_url_response")
    def test_add_locked_project_related_objects(self, role, expected_code, mocked):
        user = self.get_parameterized_test_user(role, instances=[self.project])
        self.client.force_authenticate(user)

        # Add blog entry
        payload = {
            "title": faker.sentence(),
            "content": faker.text(),
            "project_id": self.project.id,
        }
        response = self.client.post(
            reverse("BlogEntry-list", args=(self.project.id,)), data=payload
        )
        self.assertEqual(response.status_code, expected_code)

        # Add goal
        payload = {
            "title": faker.sentence(),
            "status": Goal.GoalStatus.ONGOING,
            "project_id": self.project.id,
        }
        response = self.client.post(
            reverse("Goal-list", args=(self.project.id,)),
            data=payload,
        )
        self.assertEqual(response.status_code, expected_code)

        # Add location
        payload = {
            "title": faker.word(),
            "description": faker.text(),
            "lat": float(faker.latitude()),
            "lng": float(faker.longitude()),
            "type": Location.LocationType.TEAM,
            "project_id": self.project.id,
        }
        response = self.client.post(
            reverse("Location-list", args=(self.project.id,)), data=payload
        )
        self.assertEqual(response.status_code, expected_code)

        # Add linked project
        linked_project = ProjectFactory(organizations=[self.organization])
        payload = {
            "project_id": linked_project.id,
            "target_id": self.project.id,
        }
        response = self.client.post(
            reverse("LinkedProjects-list", args=(self.project.id,)), data=payload
        )
        self.assertEqual(response.status_code, expected_code)

        # Add announcement
        payload = {
            "title": faker.sentence(),
            "description": faker.text(),
            "type": Announcement.AnnouncementType.JOB,
            "is_remunerated": faker.boolean(),
            "project_id": self.project.id,
        }
        response = self.client.post(
            reverse("Announcement-list", args=(self.project.id,)),
            data=payload,
        )
        self.assertEqual(response.status_code, expected_code)

        # Add file
        payload = {
            "mime": "text/plain",
            "title": faker.word(),
            "file": SimpleUploadedFile(
                "test_attachment_file.txt",
                b"test attachment file",
                content_type="text/plain",
            ),
            "attachment_type": AttachmentType.FILE,
            "project_id": self.project.id,
        }
        response = self.client.post(
            reverse("AttachmentFile-list", args=(self.project.id,)),
            data=payload,
            format="multipart",
        )
        self.assertEqual(response.status_code, expected_code)

        # Add link
        mocked_response = MockResponse()
        mocked.return_value = mocked_response
        payload = {
            "site_url": faker.url(),
            "project_id": self.project.id,
        }
        response = self.client.post(
            reverse("AttachmentLink-list", args=(self.project.id,)), data=payload
        )
        self.assertEqual(response.status_code, expected_code)

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_ADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_FACILITATOR, status.HTTP_200_OK),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_MEMBER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_OWNER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_REVIEWER, status.HTTP_200_OK),
        ]
    )
    def test_update_locked_project_related_objects(self, role, expected_code):
        user = self.get_parameterized_test_user(role, instances=[self.project])
        self.client.force_authenticate(user)

        # Update blog entry
        payload = {
            "title": faker.sentence(),
        }
        response = self.client.patch(
            reverse("BlogEntry-detail", args=(self.project.id, self.blog_entry.id)),
            data=payload,
        )
        self.assertEqual(response.status_code, expected_code)

        # Update goal
        payload = {
            "title": faker.sentence(),
        }
        response = self.client.patch(
            reverse("Goal-detail", args=(self.project.id, self.goal.id)),
            data=payload,
        )
        self.assertEqual(response.status_code, expected_code)

        # Update location
        payload = {
            "title": faker.word(),
        }
        response = self.client.patch(
            reverse("Location-detail", args=(self.project.id, self.location.id)),
            data=payload,
        )
        self.assertEqual(response.status_code, expected_code)

        # Update announcement
        payload = {
            "title": faker.sentence(),
        }
        response = self.client.patch(
            reverse(
                "Announcement-detail", args=(self.project.id, self.announcement.id)
            ),
            data=payload,
        )
        self.assertEqual(response.status_code, expected_code)

        # Update file
        payload = {
            "title": faker.word(),
        }
        response = self.client.patch(
            reverse(
                "AttachmentFile-detail", args=(self.project.id, self.attachment_file.id)
            ),
            data=payload,
            format="multipart",
        )
        self.assertEqual(response.status_code, expected_code)

        # Update link
        payload = {
            "site_url": faker.url(),
        }
        response = self.client.patch(
            reverse(
                "AttachmentLink-detail", args=(self.project.id, self.attachment_link.id)
            ),
            data=payload,
        )
        self.assertEqual(response.status_code, expected_code)

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_ADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_FACILITATOR, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_MEMBER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_OWNER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_REVIEWER, status.HTTP_204_NO_CONTENT),
        ]
    )
    def test_destroy_locked_project_related_objects(self, role, expected_code):
        user = self.get_parameterized_test_user(role, instances=[self.project])
        self.client.force_authenticate(user)

        # Destroy blog entry
        blog_entry = BlogEntryFactory(project=self.project)
        response = self.client.delete(
            reverse("BlogEntry-detail", args=(self.project.id, blog_entry.id))
        )
        self.assertEqual(response.status_code, expected_code)

        # Destroy goal
        goal = GoalFactory(project=self.project)
        response = self.client.delete(
            reverse("Goal-detail", args=(self.project.id, goal.id))
        )
        self.assertEqual(response.status_code, expected_code)

        # Destroy location
        location = LocationFactory(project=self.project)
        response = self.client.delete(
            reverse("Location-detail", args=(self.project.id, location.id))
        )
        self.assertEqual(response.status_code, expected_code)

        # Destroy linked project
        linked_project = LinkedProjectFactory(
            target=self.project,
            project=ProjectFactory(organizations=[self.organization]),
        )
        response = self.client.delete(
            reverse("LinkedProjects-detail", args=(self.project.id, linked_project.id))
        )
        self.assertEqual(response.status_code, expected_code)

        # Destroy announcement
        announcement = AnnouncementFactory(project=self.project)
        response = self.client.delete(
            reverse("Announcement-detail", args=(self.project.id, announcement.id))
        )
        self.assertEqual(response.status_code, expected_code)

        # Destroy file
        attachment_file = AttachmentFileFactory(project=self.project)
        response = self.client.delete(
            reverse("AttachmentFile-detail", args=(self.project.id, attachment_file.id))
        )
        self.assertEqual(response.status_code, expected_code)

        # Destroy link
        attachment_link = AttachmentLinkFactory(project=self.project)
        response = self.client.delete(
            reverse("AttachmentLink-detail", args=(self.project.id, attachment_link.id))
        )
        self.assertEqual(response.status_code, expected_code)
