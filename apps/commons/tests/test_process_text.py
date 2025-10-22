from django.urls import reverse
from faker import Faker
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase
from apps.feedbacks.factories import CommentFactory
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

faker = Faker()


class TextProcessingTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.category = ProjectCategoryFactory(organization=cls.organization)
        cls.template = TemplateFactory(
            categories=[cls.category], organization=cls.organization
        )
        cls.template_image = cls.get_test_image()
        cls.template.images.add(cls.template_image)
        cls.project = ProjectFactory(organizations=[cls.organization])
        cls.user = UserFactory(groups=[get_superadmins_group()])

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

    def test_create_comment_content(self):
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

    def test_update_comment_content(self):
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

    def test_create_template_contents(self):
        texts = [self.create_base64_image_text() for _ in range(6)]
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
        }
        response = self.client.post(
            reverse("Template-list", args=(self.organization.code,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        content = response.json()
        template = Template.objects.get(id=content["id"])
        self.assertEqual(template.images.count(), 6)
        template_id = content["id"]
        for image in template.images.all():
            self.assertIn(
                reverse(
                    "Template-images-detail",
                    args=(self.organization.code, template_id, image.id),
                ),
                content["description"]
                + content["project_description"]
                + content["project_purpose"]
                + content["goal_description"]
                + content["blogentry_content"]
                + content["review_description"],
            )

    def test_update_template_contents(self):
        self.client.force_authenticate(self.user)
        template = TemplateFactory(organization=self.organization)
        texts = [
            self.create_base64_image_text()
            + self.create_unlinked_image_text(
                "Template-images-detail", self.organization.code, template.id
            )
            for _ in range(6)
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
        }
        response = self.client.patch(
            reverse("Template-detail", args=(self.organization.code, template.id)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        template = Template.objects.get(id=content["id"])
        self.assertEqual(template.images.count(), 12)
        for image in template.images.all():
            self.assertIn(
                reverse(
                    "Template-images-detail",
                    args=(self.organization.code, template.id, image.id),
                ),
                content["description"]
                + content["project_description"]
                + content["project_purpose"]
                + content["goal_description"]
                + content["blogentry_content"]
                + content["review_description"],
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
