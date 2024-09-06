from django.urls import reverse
from faker import Faker
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase
from apps.feedbacks.factories import CommentFactory
from apps.organizations.factories import (
    FaqFactory,
    OrganizationFactory,
    ProjectCategoryFactory,
)
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
        cls.project = ProjectFactory(organizations=[cls.organization])
        cls.user = UserFactory(groups=[get_superadmins_group()])
        cls.test_image = cls.get_test_image()

    @classmethod
    def create_text_to_process(cls):
        base_64 = cls.get_base64_image()
        unlinked_image = cls.get_test_image()
        return f'<div>{base_64}</div><div><img src="/v1/path/images/{unlinked_image.id}/" alt="alt"/></div>'

    def test_create_project_description(self):
        text = self.create_text_to_process()
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
        self.assertEqual(len(response.json()["images"]), 2)

    def test_update_project_description(self):
        text = self.create_text_to_process()
        self.client.force_authenticate(self.user)
        project = self.project
        payload = {"description": text}
        response = self.client.patch(
            reverse("Project-detail", args=(project.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()["images"]), 2)

    def test_create_blog_entry_content(self):
        text = self.create_text_to_process()
        self.client.force_authenticate(self.user)
        project = self.project
        payload = {
            "title": faker.sentence(),
            "content": text,
            "project_id": project.id,
        }
        response = self.client.post(
            reverse("BlogEntry-list", args=(project.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.json()["images"]), 2)

    def test_update_blog_entry_content(self):
        text = self.create_text_to_process()
        self.client.force_authenticate(self.user)
        blog = BlogEntryFactory(project=self.project)
        payload = {"content": text}
        response = self.client.patch(
            reverse("BlogEntry-detail", args=(self.project.id, blog.id)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()["images"]), 2)

    def test_create_comment_content(self):
        text = self.create_text_to_process()
        self.client.force_authenticate(self.user)
        project = self.project
        payload = {"content": text, "project_id": project.id}
        response = self.client.post(
            reverse("Comment-list", args=(project.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        project.refresh_from_db()
        self.assertEqual(len(response.json()["images"]), 2)

    def test_update_comment_content(self):
        text = self.create_text_to_process()
        self.client.force_authenticate(self.user)
        comment = CommentFactory(project=self.project)
        payload = {"content": text}
        response = self.client.patch(
            reverse("Comment-detail", args=(self.project.id, comment.id)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()["images"]), 2)

    def test_create_faq_content(self):
        text = self.create_text_to_process()
        self.client.force_authenticate(self.user)
        organization = self.organization
        payload = {
            "title": faker.sentence(),
            "content": text,
            "organization_code": organization.code,
        }
        response = self.client.post(
            reverse("Faq-list", args=(organization.code,)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.json()["images"]), 2)

    def test_update_faq_content(self):
        text = self.create_text_to_process()
        self.client.force_authenticate(self.user)
        faq = FaqFactory()
        payload = {
            "content": text,
        }
        response = self.client.patch(
            reverse("Faq-list", args=(faq.organization.code,)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()["images"]), 2)

    def test_create_template_contents(self):
        text1 = self.create_text_to_process()
        text2 = self.create_text_to_process()
        self.client.force_authenticate(self.user)
        organization = self.organization
        payload = {
            "description": faker.text(),
            "is_reviewable": faker.boolean(),
            "name": faker.sentence(),
            "order_index": 1,
            "organization_code": organization.code,
            "template": {
                "title_placeholder": faker.sentence(),
                "goal_placeholder": faker.sentence(),
                "description_placeholder": text1,
                "blogentry_title_placeholder": faker.sentence(),
                "blogentry_placeholder": text2,
            },
        }
        response = self.client.post(reverse("Category-list"), data=payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.json()["template"]["images"]), 4)

    def test_update_template_contents(self):
        text1 = self.create_text_to_process()
        text2 = self.create_text_to_process()
        self.client.force_authenticate(self.user)
        category = ProjectCategoryFactory(organization=self.organization)
        payload = {
            "template": {
                "title_placeholder": faker.sentence(),
                "goal_placeholder": faker.sentence(),
                "description_placeholder": text1,
                "blogentry_title_placeholder": faker.sentence(),
                "blogentry_placeholder": text2,
            }
        }
        response = self.client.patch(
            reverse("Category-detail", args=(category.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()["template"]["images"]), 4)

    def test_create_project_message_content(self):
        text = self.create_text_to_process()
        self.client.force_authenticate(self.user)
        project = self.project
        payload = {
            "content": text,
        }
        response = self.client.post(
            reverse("ProjectMessage-list", args=(project.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.json()["images"]), 2)

    def test_update_project_message_content(self):
        text = self.create_text_to_process()
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
        self.assertEqual(len(response.json()["images"]), 2)
