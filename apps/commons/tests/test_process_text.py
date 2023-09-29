from django.urls import reverse

from apps.accounts.factories import UserFactory
from apps.commons.test import JwtAPITestCase
from apps.feedbacks.factories import CommentFactory
from apps.organizations.factories import (
    FaqFactory,
    OrganizationFactory,
    ProjectCategoryFactory,
)
from apps.projects.factories import BlogEntryFactory, ProjectFactory


class TextProcessingTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.test_image = cls.get_test_image()

    def create_text_to_process(self):
        base_64 = self.get_base64_image()
        unlinked_image = self.get_test_image()
        return f'<div>{base_64}</div><div><img src="/v1/path/images/{unlinked_image.id}/" alt="alt"/></div>'

    def test_create_project_description(self):
        text = self.create_text_to_process()
        org = OrganizationFactory()
        fake = ProjectFactory.build(header_image=self.test_image)
        pc = ProjectCategoryFactory(organization=org)

        self.client.force_authenticate(UserFactory())

        payload = {
            "title": fake.title,
            "description": text,
            "header_image_id": fake.header_image.id,
            "is_locked": fake.is_locked,
            "is_shareable": fake.is_shareable,
            "purpose": fake.purpose,
            "language": fake.language,
            "publication_status": fake.publication_status,
            "life_status": fake.life_status,
            "sdgs": fake.sdgs,
            "project_categories_ids": [pc.id],
            "organizations_codes": [org.code],
            "images_ids": [],
        }
        response = self.client.post(reverse("Project-list"), data=payload)
        assert response.status_code == 201
        assert len(response.json()["images"]) == 2

    def test_update_project_description(self):
        text = self.create_text_to_process()
        project = ProjectFactory()
        self.client.force_authenticate(
            UserFactory(permissions=[("projects.change_project", None)])
        )
        payload = {"description": text}
        response = self.client.patch(
            reverse("Project-detail", args=(project.id,)), data=payload
        )
        assert response.status_code == 200
        assert len(response.json()["images"]) == 2

    def test_create_blog_entry_content(self):
        text = self.create_text_to_process()
        project = ProjectFactory()
        payload = {"title": "title", "content": text, "project_id": project.id}
        self.client.force_authenticate(
            UserFactory(permissions=[("projects.change_project", None)])
        )
        response = self.client.post(
            reverse("BlogEntry-list", args=(project.id,)), data=payload
        )
        assert response.status_code == 201
        assert len(response.json()["images"]) == 2

    def test_update_blog_entry_content(self):
        text = self.create_text_to_process()
        blog = BlogEntryFactory()
        payload = {"content": text}
        self.client.force_authenticate(
            UserFactory(permissions=[("projects.change_project", None)])
        )
        response = self.client.patch(
            reverse("BlogEntry-detail", args=(blog.project.id, blog.id)), data=payload
        )
        assert response.status_code == 200
        assert len(response.json()["images"]) == 2

    def test_create_comment_content(self):
        text = self.create_text_to_process()
        project = ProjectFactory()
        payload = {"content": text, "project_id": project.id}
        self.client.force_authenticate(UserFactory())
        response = self.client.post(
            reverse("Comment-list", args=(project.id,)), data=payload
        )
        assert response.status_code == 201
        project.refresh_from_db()
        assert len(response.json()["images"]) == 2

    def test_update_comment_content(self):
        text = self.create_text_to_process()
        comment = CommentFactory()
        self.client.force_authenticate(
            UserFactory(permissions=[("feedbacks.change_comment", None)])
        )
        payload = {"content": text}
        response = self.client.patch(
            reverse("Comment-detail", args=(comment.project.id, comment.id)),
            data=payload,
        )
        assert response.status_code == 200
        assert len(response.json()["images"]) == 2

    def test_create_faq_content(self):
        text = self.create_text_to_process()
        organization = OrganizationFactory()
        self.client.force_authenticate(
            UserFactory(permissions=[("organizations.add_faq", organization)])
        )
        payload = {
            "title": "title",
            "content": text,
            "organization_code": organization.code,
        }
        response = self.client.post(
            reverse("Faq-list", args=[organization.code]),
            data=payload,
        )
        assert response.status_code == 201
        assert len(response.json()["images"]) == 2

    def test_update_faq_content(self):
        text = self.create_text_to_process()
        organization = OrganizationFactory()
        self.client.force_authenticate(
            UserFactory(permissions=[("organizations.change_faq", organization)])
        )
        FaqFactory(organization=organization)
        payload = {
            "content": text,
        }
        response = self.client.patch(
            reverse("Faq-list", args=[organization.code]),
            data=payload,
        )
        assert response.status_code == 200
        assert len(response.json()["images"]) == 2

    def test_create_template_contents(self):
        text1 = self.create_text_to_process()
        text2 = self.create_text_to_process()
        organization = OrganizationFactory()
        self.client.force_authenticate(
            UserFactory(
                permissions=[("organizations.add_projectcategory", organization)]
            ),
        )
        fake = ProjectCategoryFactory.build(organization=organization)
        payload = {
            "background_color": fake.background_color,
            "description": fake.description,
            "foreground_color": fake.foreground_color,
            "is_reviewable": fake.is_reviewable,
            "name": fake.name,
            "order_index": fake.order_index,
            "organization_code": organization.code,
            "template": {
                "title_placeholder": "title",
                "goal_placeholder": "goal",
                "description_placeholder": text1,
                "blogentry_title_placeholder": "blog",
                "blogentry_placeholder": text2,
            },
        }
        response = self.client.post(
            reverse("Category-list"), data=payload, format="json"
        )
        assert response.status_code == 201
        assert len(response.json()["template"]["images"]) == 4

    def test_update_template_contents(self):
        text1 = self.create_text_to_process()
        text2 = self.create_text_to_process()
        category = ProjectCategoryFactory()
        self.client.force_authenticate(
            UserFactory(
                permissions=[
                    ("organizations.change_projectcategory", category.organization)
                ]
            ),
        )
        payload = {
            "template": {
                "title_placeholder": "title",
                "goal_placeholder": "goal",
                "description_placeholder": text1,
                "blogentry_title_placeholder": "blog",
                "blogentry_placeholder": text2,
            }
        }
        response = self.client.patch(
            reverse("Category-detail", args=(category.id,)), data=payload, format="json"
        )
        assert response.status_code == 200
        assert len(response.json()["template"]["images"]) == 4
