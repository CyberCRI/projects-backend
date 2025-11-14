from django.core.management import call_command
from django.urls import reverse
from faker import Faker

from apps.accounts.factories import PeopleGroupFactory, UserFactory
from apps.announcements.factories import AnnouncementFactory
from apps.commons.test import JwtAPITestCase
from apps.feedbacks.factories import CommentFactory, ReviewFactory
from apps.files.factories import (
    AttachmentFileFactory,
    AttachmentLinkFactory,
    OrganizationAttachmentFileFactory,
)
from apps.invitations.factories import AccessRequestFactory
from apps.newsfeed.factories import EventFactory, InstructionFactory, NewsFactory
from apps.organizations.factories import (
    OrganizationFactory,
    ProjectCategoryFactory,
    TemplateFactory,
)
from apps.projects.factories import (
    BlogEntryFactory,
    GoalFactory,
    LocationFactory,
    ProjectFactory,
    ProjectMessageFactory,
    ProjectTabFactory,
    ProjectTabItemFactory,
)
from apps.projects.models import Project
from apps.skills.factories import MentoringMessageFactory

faker = Faker()


class TextProcessingTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        organization = OrganizationFactory()
        category = ProjectCategoryFactory(organization=organization, is_reviewable=True)
        template = TemplateFactory(categories=[category], organization=organization)
        template_image = cls.get_test_image()
        template.images.add(template_image)
        project = ProjectFactory(
            organizations=[organization],
            categories=[category],
            life_status=Project.LifeStatus.TO_REVIEW,
        )

        cls.base64_image_text = cls.create_base64_image_text()

        cls.people_group = PeopleGroupFactory(
            organization=organization,
            description=cls.base64_image_text,
            short_description=cls.base64_image_text,
        )
        cls.user = UserFactory(
            description=cls.base64_image_text,
            short_description=cls.base64_image_text,
        )
        cls.announcement = AnnouncementFactory(
            project=project,
            description=cls.base64_image_text,
        )
        cls.comment = CommentFactory(
            project=project,
            content=(
                cls.base64_image_text
                + cls.create_template_image_text(
                    organization.code, template.id, template_image.id
                )
                + cls.create_unlinked_image_text("Comment-images-detail", project.id)
            ),
        )
        cls.review = ReviewFactory(
            project=project,
            description=cls.base64_image_text,
        )
        cls.org_attachment_file = OrganizationAttachmentFileFactory(
            organization=organization,
            description=cls.base64_image_text,
        )
        cls.attachment_link = AttachmentLinkFactory(
            project=project,
            description=cls.base64_image_text,
        )
        cls.attachment_file = AttachmentFileFactory(
            project=project,
            description=cls.base64_image_text,
        )
        cls.access_request = AccessRequestFactory(
            organization=organization,
            message=cls.base64_image_text,
        )
        cls.news = NewsFactory(organization=organization, content=cls.base64_image_text)
        cls.news.content += cls.create_unlinked_image_text(
            "News-images-detail", organization.code, cls.news.id
        )
        cls.news.save()
        cls.event = EventFactory(
            organization=organization, content=cls.base64_image_text
        )
        cls.event.content += cls.create_unlinked_image_text(
            "Event-images-detail", organization.code, cls.event.id
        )
        cls.event.save()
        cls.instruction = InstructionFactory(
            organization=organization, content=cls.base64_image_text
        )
        cls.instruction.content += cls.create_unlinked_image_text(
            "Instruction-images-detail", organization.code, cls.instruction.id
        )
        cls.instruction.save()
        cls.organization = OrganizationFactory(
            description=cls.base64_image_text,
        )
        cls.organization.description += cls.create_unlinked_image_text(
            "Organization-images-detail", cls.organization.code
        )
        cls.organization.save()
        cls.terms_and_conditions = cls.organization.terms_and_conditions
        cls.terms_and_conditions.content = cls.base64_image_text
        cls.terms_and_conditions.save()
        cls.template = TemplateFactory(
            organization=organization,
            description=cls.base64_image_text,
            project_description=cls.base64_image_text,
            project_purpose=cls.base64_image_text,
            blogentry_content=cls.base64_image_text,
            goal_description=cls.base64_image_text,
            review_description=cls.base64_image_text,
            comment_content=cls.base64_image_text,
        )
        for field in [
            "description",
            "project_description",
            "blogentry_content",
            "comment_content",
        ]:
            setattr(
                cls.template,
                field,
                getattr(cls.template, field)
                + cls.create_unlinked_image_text(
                    "Template-images-detail", organization.code, cls.template.id
                ),
            )
        cls.template.save()
        cls.category = ProjectCategoryFactory(
            organization=organization,
            description=cls.base64_image_text,
        )
        cls.project = ProjectFactory(
            organizations=[organization],
            categories=[category],
            description=cls.base64_image_text
            + cls.create_template_image_text(
                organization.code, template.id, template_image.id
            ),
        )
        cls.project.description += cls.create_unlinked_image_text(
            "Project-images-detail", cls.project.id
        )
        cls.project.save()
        cls.blog_entry = BlogEntryFactory(
            project=project,
            content=(
                cls.base64_image_text
                + cls.create_template_image_text(
                    organization.code, template.id, template_image.id
                )
                + cls.create_unlinked_image_text(
                    "BlogEntry-images-detail", cls.project.id
                )
            ),
        )
        cls.project_message = ProjectMessageFactory(
            project=project,
            content=cls.base64_image_text
            + cls.create_unlinked_image_text(
                "ProjectMessage-images-detail", cls.project.id
            ),
        )
        cls.goal = GoalFactory(
            project=project,
            description=cls.base64_image_text,
        )
        cls.location = LocationFactory(
            project=project,
            description=cls.base64_image_text,
        )
        cls.project_tab = ProjectTabFactory(
            project=project,
            description=(
                cls.base64_image_text
                + cls.create_unlinked_image_text(
                    "ProjectTab-images-detail", cls.project.id
                )
            ),
        )
        cls.project_tab_item = ProjectTabItemFactory(
            tab=cls.project_tab,
            content=(
                cls.base64_image_text
                + cls.create_unlinked_image_text(
                    "ProjectTabItem-images-detail", cls.project.id, cls.project_tab.id
                )
            ),
        )
        cls.mentoring_message = MentoringMessageFactory(content=cls.base64_image_text)

    @classmethod
    def create_base64_image_text(cls):
        return f"<p>Untouched text base64</p>{cls.get_base64_image()}"

    @classmethod
    def create_unlinked_image_text(cls, view: str, *args):
        unlinked_image = cls.get_test_image()
        unlinked_image_path = reverse(view, args=(*args, unlinked_image.id))
        return f'<p>Untouched text unlinked</p><img src="{unlinked_image_path}" alt="alt"/>'

    @classmethod
    def create_template_image_text(
        cls,
        organization_code: str = None,
        template_id: int = None,
        template_image_id: int = None,
    ):
        return f'<p>Untouched text template</p><img src="{reverse("Template-images-detail", args=(organization_code, template_id, template_image_id))}" alt="alt"/></p>'

    def test_remove_base64_images(self):
        call_command("remove_base64_images")
        # Get initial contents

        # Refresh from db
        self.people_group.refresh_from_db()
        self.user.refresh_from_db()
        self.announcement.refresh_from_db()
        self.comment.refresh_from_db()
        self.review.refresh_from_db()
        self.org_attachment_file.refresh_from_db()
        self.attachment_link.refresh_from_db()
        self.attachment_file.refresh_from_db()
        self.access_request.refresh_from_db()
        self.news.refresh_from_db()
        self.event.refresh_from_db()
        self.instruction.refresh_from_db()
        self.organization.refresh_from_db()
        self.terms_and_conditions.refresh_from_db()
        self.template.refresh_from_db()
        self.category.refresh_from_db()
        self.project.refresh_from_db()
        self.blog_entry.refresh_from_db()
        self.project_message.refresh_from_db()
        self.goal.refresh_from_db()
        self.location.refresh_from_db()
        self.project_tab.refresh_from_db()
        self.project_tab_item.refresh_from_db()
        self.mentoring_message.refresh_from_db()

        # Check base64 images removed
        self.assertEqual(self.people_group.description, "<p>Untouched text base64</p>")
        self.assertEqual(self.user.description, "<p>Untouched text base64</p>")
        self.assertEqual(self.announcement.description, "<p>Untouched text base64</p>")
        self.assertNotIn('<img src="data:image/png;base64,', self.comment.content)
        self.assertEqual(self.comment.content.count("<img src="), 3)
        self.assertEqual(self.review.description, "<p>Untouched text base64</p>")
        self.assertEqual(
            self.org_attachment_file.description, "<p>Untouched text base64</p>"
        )
        self.assertEqual(
            self.attachment_link.description, "<p>Untouched text base64</p>"
        )
        self.assertEqual(
            self.attachment_file.description, "<p>Untouched text base64</p>"
        )
        self.assertEqual(self.access_request.message, "<p>Untouched text base64</p>")
        self.assertNotIn('<img src="data:image/png;base64,', self.news.content)
        self.assertEqual(self.news.content.count("<img src="), 2)
        self.assertNotIn('<img src="data:image/png;base64,', self.event.content)
        self.assertEqual(self.event.content.count("<img src="), 2)
        self.assertNotIn('<img src="data:image/png;base64,', self.instruction.content)
        self.assertEqual(self.instruction.content.count("<img src="), 2)
        self.assertNotIn(
            '<img src="data:image/png;base64,', self.organization.description
        )
        self.assertEqual(self.organization.description.count("<img src="), 2)
        self.assertEqual(
            self.terms_and_conditions.content, "<p>Untouched text base64</p>"
        )
        self.assertNotIn('<img src="data:image/png;base64,', self.template.description)
        self.assertEqual(self.template.description.count("<img src="), 2)
        self.assertNotIn(
            '<img src="data:image/png;base64,', self.template.project_description
        )
        self.assertEqual(self.template.project_description.count("<img src="), 2)
        self.assertEqual(self.template.project_purpose, "<p>Untouched text base64</p>")
        self.assertNotIn(
            '<img src="data:image/png;base64,', self.template.blogentry_content
        )
        self.assertEqual(self.template.blogentry_content.count("<img src="), 2)
        self.assertEqual(self.template.goal_description, "<p>Untouched text base64</p>")
        self.assertEqual(
            self.template.review_description, "<p>Untouched text base64</p>"
        )
        self.assertNotIn(
            '<img src="data:image/png;base64,', self.template.comment_content
        )
        self.assertEqual(self.template.comment_content.count("<img src="), 2)
        self.assertNotIn('<img src="data:image/png;base64,', self.project.description)
        self.assertEqual(self.project.description.count("<img src="), 3)
        self.assertNotIn('<img src="data:image/png;base64,', self.blog_entry.content)
        self.assertEqual(self.blog_entry.content.count("<img src="), 3)
        self.assertNotIn(
            '<img src="data:image/png;base64,', self.project_message.content
        )
        self.assertEqual(self.project_message.content.count("<img src="), 2)
        self.assertEqual(self.goal.description, "<p>Untouched text base64</p>")
        self.assertEqual(self.location.description, "<p>Untouched text base64</p>")
        self.assertNotIn(
            '<img src="data:image/png;base64,', self.project_tab.description
        )
        self.assertEqual(self.project_tab.description.count("<img src="), 2)
        self.assertNotIn(
            '<img src="data:image/png;base64,', self.project_tab_item.content
        )
        self.assertEqual(self.project_tab_item.content.count("<img src="), 2)
        self.assertEqual(self.mentoring_message.content, "<p>Untouched text base64</p>")
