import datetime
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from faker import Faker
from rest_framework import status

from apps.accounts.factories import PeopleGroupFactory, UserFactory
from apps.accounts.utils import get_superadmins_group
from apps.announcements.models import Announcement
from apps.commons.test import JwtAPITestCase
from apps.feedbacks.factories import CommentFactory
from apps.files.enums import AttachmentType
from apps.files.tests.views.mock_response import MockResponse
from apps.newsfeed.factories import EventFactory, InstructionFactory, NewsFactory
from apps.newsfeed.models import Event, Instruction, News
from apps.organizations.factories import (
    OrganizationFactory,
    ProjectCategoryFactory,
    TemplateFactory,
)
from apps.organizations.models import Template
from apps.projects.factories import (
    BlogEntryFactory,
    ProjectFactory,
    ProjectMessageFactory,
)
from apps.projects.models import Project

faker = Faker()


class TextProcessingTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.category = ProjectCategoryFactory(
            organization=cls.organization, is_reviewable=True
        )
        cls.template = TemplateFactory(
            categories=[cls.category], organization=cls.organization
        )
        cls.template_image = cls.get_test_image()
        cls.template.images.add(cls.template_image)
        cls.project = ProjectFactory(
            organizations=[cls.organization],
            categories=[cls.category],
            life_status=Project.LifeStatus.TO_REVIEW,
        )
        cls.user = UserFactory(
            groups=[get_superadmins_group(), cls.project.get_reviewers()]
        )
        cls.people_group = PeopleGroupFactory(organization=cls.organization)

    @classmethod
    def create_base64_image_text(cls):
        return f"<div>{cls.get_base64_image()}</div"

    @classmethod
    def create_unlinked_image_text(cls, view: str, *args):
        unlinked_image = cls.get_test_image()
        unlinked_image_path = reverse(view, args=(*args, unlinked_image.id))
        return f'<div><img src="{unlinked_image_path}" alt="alt"/></div>'

    @classmethod
    def create_template_image_text(cls):
        return f'<div><img src="{reverse("Template-images-detail", args=(cls.organization.code, cls.template.id, cls.template_image.id))}" alt="alt"/></div>'

    def test_group(self):
        texts = [self.create_base64_image_text() for _ in range(2)]
        self.client.force_authenticate(self.user)
        payload = {
            "name": faker.sentence(),
            "description": texts[0],
            "short_description": texts[1],
        }
        response = self.client.post(
            reverse("PeopleGroup-list", args=(self.organization.code,)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        content = response.json()
        self.assertNotIn("<img", content["description"] + content["short_description"])

        payload = {
            "description": texts[0],
            "short_description": texts[1],
        }
        response = self.client.patch(
            reverse(
                "PeopleGroup-detail",
                args=(self.organization.code, content["id"]),
            ),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertNotIn("<img", content["description"] + content["short_description"])

    @patch("services.keycloak.interface.KeycloakService.send_email")
    def test_user(self, mocked):
        mocked.return_value = {}
        texts = [self.create_base64_image_text() for _ in range(2)]
        self.client.force_authenticate(self.user)
        payload = {
            "username": faker.user_name(),
            "email": faker.email(),
            "first_name": faker.first_name(),
            "last_name": faker.last_name(),
            "description": texts[0],
            "short_description": texts[1],
        }
        response = self.client.post(
            reverse("ProjectUser-list") + f"?organization={self.organization.code}",
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        content = response.json()
        self.assertNotIn("<img", content["description"] + content["short_description"])

        payload = {
            "description": texts[0],
            "short_description": texts[1],
        }
        response = self.client.patch(
            reverse("ProjectUser-detail", args=(content["id"],)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertNotIn("<img", content["description"] + content["short_description"])

    def test_announcement(self):
        text = self.create_base64_image_text()
        self.client.force_authenticate(self.user)
        payload = {
            "type": Announcement.AnnouncementType.JOB,
            "is_remunerated": faker.boolean(),
            "project_id": self.project.id,
            "title": faker.sentence(),
            "description": text,
        }
        response = self.client.post(
            reverse("Announcement-list", args=(self.project.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        content = response.json()
        self.assertNotIn("<img", content["description"])

        payload = {"description": text}
        response = self.client.patch(
            reverse(
                "Announcement-detail",
                args=(self.project.id, content["id"]),
            ),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertNotIn("<img", content["description"])

    def test_create_comment(self):
        text = (
            self.create_base64_image_text()
            + self.create_template_image_text()
            + self.create_unlinked_image_text("Comment-images-detail", self.project.id)
        )
        self.client.force_authenticate(self.user)
        project = self.project
        payload = {"content": text, "project_id": project.id}
        response = self.client.post(
            reverse("Comment-list", args=(project.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        content = response.json()
        self.assertEqual(len(content["images"]), 3)
        for image_id in content["images"]:
            self.assertIn(
                reverse("Comment-images-detail", args=(project.id, image_id)),
                content["content"],
            )

    def test_update_comment(self):
        text = (
            self.create_base64_image_text()
            + self.create_template_image_text()
            + self.create_unlinked_image_text("Comment-images-detail", self.project.id)
        )
        self.client.force_authenticate(self.user)
        comment = CommentFactory(project=self.project)
        payload = {"content": text}
        response = self.client.patch(
            reverse("Comment-detail", args=(self.project.id, comment.id)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(len(content["images"]), 3)
        for image_id in content["images"]:
            self.assertIn(
                reverse("Comment-images-detail", args=(self.project.id, image_id)),
                content["content"],
            )

    def test_review(self):
        text = self.create_base64_image_text()
        self.client.force_authenticate(self.user)
        payload = {
            "title": faker.sentence(),
            "description": text,
            "project_id": self.project.id,
        }
        response = self.client.post(
            reverse("Reviewed-list", args=(self.project.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        content = response.json()
        self.assertNotIn("<img", content["description"])

        payload = {"description": text}
        response = self.client.patch(
            reverse("Reviewed-detail", args=(self.project.id, content["id"])),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertNotIn("<img", content["description"])

    def test_organization_attachment_file(self):
        text = self.create_base64_image_text()
        self.client.force_authenticate(self.user)
        payload = {
            "mime": "text/plain",
            "title": faker.text(max_nb_chars=50),
            "description": text,
            "file": SimpleUploadedFile(
                "test_attachment_file.txt",
                b"test attachment file",
                content_type="text/plain",
            ),
            "attachment_type": AttachmentType.FILE,
        }
        response = self.client.post(
            reverse("OrganizationAttachmentFile-list", args=(self.organization.code,)),
            data=payload,
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        content = response.json()
        self.assertNotIn("<img", content["description"])

        payload = {"description": text}
        response = self.client.patch(
            reverse(
                "OrganizationAttachmentFile-detail",
                args=(self.organization.code, content["id"]),
            ),
            data=payload,
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertNotIn("<img", content["description"])

    @patch("apps.files.serializers.AttachmentLinkSerializer.get_url_response")
    def test_attachment_link(self, mocked):
        mocked_response = MockResponse()
        mocked.return_value = mocked_response
        text = self.create_base64_image_text()
        self.client.force_authenticate(self.user)
        payload = {
            "site_url": faker.url(),
            "project_id": self.project.id,
            "description": text,
        }
        response = self.client.post(
            reverse("AttachmentLink-list", args=(self.project.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        content = response.json()
        self.assertNotIn("<img", content["description"])

        payload = {"description": text}
        response = self.client.patch(
            reverse(
                "AttachmentLink-detail",
                args=(self.project.id, content["id"]),
            ),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertNotIn("<img", content["description"])

    def test_attachment_file(self):
        text = self.create_base64_image_text()
        self.client.force_authenticate(self.user)
        payload = {
            "mime": "text/plain",
            "title": faker.text(max_nb_chars=50),
            "description": text,
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
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        content = response.json()
        self.assertNotIn("<img", content["description"])

        payload = {"description": text}
        response = self.client.patch(
            reverse(
                "AttachmentFile-detail",
                args=(self.project.id, content["id"]),
            ),
            data=payload,
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertNotIn("<img", content["description"])

    def test_access_request(self):
        text = self.create_base64_image_text()
        self.client.force_authenticate(self.user)
        payload = {
            "email": faker.email(),
            "given_name": faker.first_name(),
            "family_name": faker.last_name(),
            "job": faker.sentence(),
            "message": text,
        }
        response = self.client.post(
            reverse("AccessRequest-list", args=(self.organization.code,)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        content = response.json()
        self.assertNotIn("<img", content["message"])

    def test_create_news(self):
        text = self.create_base64_image_text()
        self.client.force_authenticate(self.user)
        payload = {
            "organization": self.organization.code,
            "title": faker.sentence(),
            "content": text,
            "publication_date": datetime.date.today().isoformat(),
            "people_groups": [self.people_group.id],
        }
        response = self.client.post(
            reverse("News-list", args=(self.organization.code,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        content = response.json()
        news = News.objects.get(id=content["id"])
        self.assertEqual(news.images.count(), 1)
        for image_id in news.images.values_list("id", flat=True):
            self.assertIn(
                reverse(
                    "News-images-detail",
                    args=(self.organization.code, news.id, image_id),
                ),
                content["content"],
            )

    def test_update_news(self):
        news = NewsFactory(organization=self.organization)
        text = self.create_base64_image_text() + self.create_unlinked_image_text(
            "News-images-detail", self.organization.code, news.id
        )
        self.client.force_authenticate(self.user)
        payload = {"content": text}
        response = self.client.patch(
            reverse("News-detail", args=(self.organization.code, news.id)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        news.refresh_from_db()
        self.assertEqual(news.images.count(), 2)
        content = response.json()
        for image_id in news.images.values_list("id", flat=True):
            self.assertIn(
                reverse(
                    "News-images-detail",
                    args=(self.organization.code, news.id, image_id),
                ),
                content["content"],
            )

    def test_create_event(self):
        text = self.create_base64_image_text()
        self.client.force_authenticate(self.user)
        payload = {
            "organization": self.organization.code,
            "title": faker.sentence(),
            "content": text,
            "event_date": datetime.date.today().isoformat(),
            "people_groups": [self.people_group.id],
        }

        response = self.client.post(
            reverse("Event-list", args=(self.organization.code,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        content = response.json()
        event = Event.objects.get(id=content["id"])
        self.assertEqual(event.images.count(), 1)
        for image_id in event.images.values_list("id", flat=True):
            self.assertIn(
                reverse(
                    "Event-images-detail",
                    args=(self.organization.code, event.id, image_id),
                ),
                content["content"],
            )

    def test_update_event(self):
        event = EventFactory(organization=self.organization)
        text = self.create_base64_image_text() + self.create_unlinked_image_text(
            "Event-images-detail", self.organization.code, event.id
        )
        self.client.force_authenticate(self.user)
        payload = {"content": text}
        response = self.client.patch(
            reverse("Event-detail", args=(self.organization.code, event.id)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        event.refresh_from_db()
        self.assertEqual(event.images.count(), 2)
        for image_id in event.images.values_list("id", flat=True):
            self.assertIn(
                reverse(
                    "Event-images-detail",
                    args=(self.organization.code, event.id, image_id),
                ),
                content["content"],
            )

    def test_create_instruction(self):
        text = self.create_base64_image_text()
        self.client.force_authenticate(self.user)
        payload = {
            "title": faker.sentence(),
            "content": text,
            "language": "fr",
            "publication_date": datetime.date.today().isoformat(),
            "has_to_be_notified": True,
        }
        response = self.client.post(
            reverse("Instruction-list", args=(self.organization.code,)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        content = response.json()
        instruction = Instruction.objects.get(id=content["id"])
        self.assertEqual(instruction.images.count(), 1)
        for image_id in instruction.images.values_list("id", flat=True):
            self.assertIn(
                reverse(
                    "Instruction-images-detail",
                    args=(self.organization.code, instruction.id, image_id),
                ),
                content["content"],
            )

    def test_update_instruction(self):
        instruction = InstructionFactory(organization=self.organization)
        text = self.create_base64_image_text() + self.create_unlinked_image_text(
            "Instruction-images-detail", self.organization.code, instruction.id
        )
        self.client.force_authenticate(self.user)
        payload = {"content": text}
        response = self.client.patch(
            reverse(
                "Instruction-detail", args=(self.organization.code, instruction.id)
            ),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        instruction.refresh_from_db()
        self.assertEqual(instruction.images.count(), 2)
        for image_id in instruction.images.values_list("id", flat=True):
            self.assertIn(
                reverse(
                    "Instruction-images-detail",
                    args=(self.organization.code, instruction.id, image_id),
                ),
                content["content"],
            )

    def test_create_project_description(self):
        text = self.create_base64_image_text() + self.create_template_image_text()
        self.client.force_authenticate(self.user)
        payload = {
            "title": faker.sentence(),
            "description": text,
            "is_locked": faker.boolean(),
            "is_shareable": faker.boolean(),
            "purpose": faker.sentence(),
            "organizations_codes": [self.organization.code],
            "images_ids": [],
        }
        response = self.client.post(reverse("Project-list"), data=payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        content = response.json()
        self.assertEqual(len(content["images"]), 2)
        project_id = content["id"]
        for image in content["images"]:
            image_id = image["id"]
            self.assertIn(
                reverse("Project-images-detail", args=(project_id, image_id)),
                content["description"],
            )

    def test_update_project_description(self):
        text = (
            self.create_base64_image_text()
            + self.create_template_image_text()
            + self.create_unlinked_image_text("Project-images-detail", self.project.id)
        )
        self.client.force_authenticate(self.user)
        payload = {"description": text}
        response = self.client.patch(
            reverse("Project-detail", args=(self.project.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(len(content["images"]), 3)
        for image in content["images"]:
            image_id = image["id"]
            self.assertIn(
                reverse("Project-images-detail", args=(self.project.id, image_id)),
                content["description"],
            )

    def test_create_blog_entry_content(self):
        text = (
            self.create_base64_image_text()
            + self.create_template_image_text()
            + self.create_unlinked_image_text(
                "BlogEntry-images-detail", self.project.id
            )
        )
        self.client.force_authenticate(self.user)
        payload = {
            "title": faker.sentence(),
            "content": text,
            "project_id": self.project.id,
        }
        response = self.client.post(
            reverse("BlogEntry-list", args=(self.project.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        content = response.json()
        self.assertEqual(len(content["images"]), 3)
        for image_id in content["images"]:
            self.assertIn(
                reverse("BlogEntry-images-detail", args=(self.project.id, image_id)),
                content["content"],
            )

    def test_update_blog_entry_content(self):
        text = (
            self.create_base64_image_text()
            + self.create_template_image_text()
            + self.create_unlinked_image_text(
                "BlogEntry-images-detail", self.project.id
            )
        )
        self.client.force_authenticate(self.user)
        blog = BlogEntryFactory(project=self.project)
        payload = {"content": text}
        response = self.client.patch(
            reverse("BlogEntry-detail", args=(self.project.id, blog.id)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(len(content["images"]), 3)
        for image_id in content["images"]:
            self.assertIn(
                reverse("BlogEntry-images-detail", args=(self.project.id, image_id)),
                content["content"],
            )

    def test_create_template_contents(self):
        texts = [self.create_base64_image_text() for _ in range(7)]
        self.client.force_authenticate(self.user)
        payload = {
            "name": faker.sentence(),
            "description": texts[0],
            "project_title": faker.sentence(),
            "project_description": texts[1],
            "project_purpose": texts[2],
            "blogentry_title": faker.sentence(),
            "blogentry_content": texts[3],
            "goal_title": faker.sentence(),
            "goal_description": texts[4],
            "review_title": faker.sentence(),
            "review_description": texts[5],
            "comment_content": texts[6],
        }
        response = self.client.post(
            reverse("Template-list", args=(self.organization.code,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        content = response.json()
        template = Template.objects.get(id=content["id"])
        self.assertEqual(template.images.count(), 3)
        template_id = content["id"]
        for image in template.images.all():
            self.assertIn(
                reverse(
                    "Template-images-detail",
                    args=(self.organization.code, template_id, image.id),
                ),
                content["project_description"]
                + content["blogentry_content"]
                + content["comment_content"],
            )

    def test_update_template_contents(self):
        self.client.force_authenticate(self.user)
        template = TemplateFactory(organization=self.organization)
        texts = [
            self.create_base64_image_text()
            + self.create_unlinked_image_text(
                "Template-images-detail", self.organization.code, template.id
            )
            for _ in range(7)
        ]
        payload = {
            "name": faker.sentence(),
            "description": texts[0],
            "project_title": faker.sentence(),
            "project_description": texts[1],
            "project_purpose": texts[2],
            "blogentry_title": faker.sentence(),
            "blogentry_content": texts[3],
            "goal_title": faker.sentence(),
            "goal_description": texts[4],
            "review_title": faker.sentence(),
            "review_description": texts[5],
            "comment_content": texts[6],
        }
        response = self.client.patch(
            reverse("Template-detail", args=(self.organization.code, template.id)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        template = Template.objects.get(id=content["id"])
        self.assertEqual(template.images.count(), 6)
        for image in template.images.all():
            self.assertIn(
                reverse(
                    "Template-images-detail",
                    args=(self.organization.code, template.id, image.id),
                ),
                content["project_description"]
                + content["blogentry_content"]
                + content["comment_content"],
            )

    def test_create_project_message_content(self):
        text = self.create_base64_image_text() + self.create_unlinked_image_text(
            "ProjectMessage-images-detail", self.project.id
        )
        self.client.force_authenticate(self.user)
        payload = {
            "content": text,
        }
        response = self.client.post(
            reverse("ProjectMessage-list", args=(self.project.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        content = response.json()
        self.assertEqual(len(content["images"]), 2)
        for image_id in content["images"]:
            self.assertIn(
                reverse(
                    "ProjectMessage-images-detail", args=(self.project.id, image_id)
                ),
                content["content"],
            )

    def test_update_project_message_content(self):
        text = self.create_base64_image_text() + self.create_unlinked_image_text(
            "ProjectMessage-images-detail", self.project.id
        )
        self.client.force_authenticate(self.user)
        project_message = ProjectMessageFactory(project=self.project)
        payload = {"content": text}
        response = self.client.patch(
            reverse(
                "ProjectMessage-detail", args=(self.project.id, project_message.id)
            ),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(len(content["images"]), 2)
        for image_id in content["images"]:
            self.assertIn(
                reverse(
                    "ProjectMessage-images-detail", args=(self.project.id, image_id)
                ),
                content["content"],
            )
