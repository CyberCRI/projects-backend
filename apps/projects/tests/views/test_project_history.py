from unittest.mock import patch

from django.apps import apps
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from faker import Faker
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.accounts.utils import get_superadmins_group
from apps.announcements.factories import AnnouncementFactory
from apps.announcements.models import Announcement
from apps.commons.models import GroupData
from apps.commons.test import JwtAPITestCase
from apps.feedbacks.factories import CommentFactory
from apps.files.enums import AttachmentType
from apps.files.factories import AttachmentFileFactory, AttachmentLinkFactory
from apps.files.tests.views.mock_response import MockResponse
from apps.organizations.factories import OrganizationFactory, ProjectCategoryFactory
from apps.projects.factories import (
    BlogEntryFactory,
    GoalFactory,
    LinkedProjectFactory,
    LocationFactory,
    ProjectFactory,
)
from apps.projects.models import Goal, Location
from apps.skills.factories import TagFactory

faker = Faker()

HistoricalProject = apps.get_model("projects", "HistoricalProject")


class ProjectHistoryTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.user = UserFactory(groups=[get_superadmins_group()])

    def test_create_project(self):
        self.client.force_authenticate(self.user)
        payload = {
            "title": faker.sentence(),
            "description": faker.text(),
            "purpose": faker.sentence(),
            "organizations_codes": [self.organization.code],
        }
        response = self.client.post(reverse("Project-list"), data=payload)
        project_id = response.json()["id"]
        history = HistoricalProject.objects.filter(history_relation__id=project_id)
        latest_version = history.order_by("-history_date").first()
        response = self.client.get(
            reverse("Project-versions-detail", args=(project_id, latest_version.pk))
        )
        version = response.json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(version["history_change_reason"], "Created project")
        self.assertIn(self.user.get_full_name(), version["members"])

    def test_add_project_member(self):
        project = ProjectFactory(organizations=[self.organization])
        updated_at = project.updated_at
        self.client.force_authenticate(self.user)
        initial_count = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        payload = {
            GroupData.Role.MEMBERS: [self.user.id],
        }
        self.client.post(
            reverse("Project-add-member", args=(project.id,)),
            data=payload,
        )
        history = HistoricalProject.objects.filter(history_relation__id=project.id)
        latest_version = history.order_by("-history_date").first()
        response = self.client.get(
            reverse("Project-versions-detail", args=(project.id, latest_version.pk))
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count(),
            initial_count + 1,
        )
        self.assertEqual(response.json()["history_change_reason"], "Added members")
        project.refresh_from_db()
        self.assertNotEqual(updated_at, project.updated_at)

    def test_remove_project_member(self):
        project = ProjectFactory(organizations=[self.organization], with_owner=True)
        updated_at = project.updated_at
        self.client.force_authenticate(self.user)
        initial_count = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        project.members.add(self.user)
        payload = {
            "users": [self.user.id],
        }
        self.client.post(
            reverse("Project-remove-member", args=(project.id,)),
            data=payload,
        )
        history = HistoricalProject.objects.filter(history_relation__id=project.id)
        latest_version = history.order_by("-history_date").first()
        response = self.client.get(
            reverse("Project-versions-detail", args=(project.id, latest_version.pk))
        )
        version = response.json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count(),
            initial_count + 1,
        )
        self.assertNotIn(self.user.get_full_name(), version["members"])
        self.assertEqual(version["history_change_reason"], "Removed members")
        project.refresh_from_db()
        self.assertNotEqual(updated_at, project.updated_at)

    def test_add_comment(self):
        project = ProjectFactory(organizations=[self.organization])
        updated_at = project.updated_at
        self.client.force_authenticate(self.user)
        initial_count = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        payload = {
            "project_id": project.id,
            "content": faker.text(),
        }
        response = self.client.post(
            reverse("Comment-list", args=(project.id,)),
            data=payload,
        )
        comment_id = response.json()["id"]
        history = HistoricalProject.objects.filter(history_relation__id=project.id)
        latest_version = history.order_by("-history_date").first()
        response = self.client.get(
            reverse("Project-versions-detail", args=(project.id, latest_version.pk))
        )
        version = response.json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count(),
            initial_count + 1,
        )
        self.assertIn(comment_id, [c["id"] for c in version["comments"]])
        self.assertEqual(version["history_change_reason"], "Added comment")
        project.refresh_from_db()
        self.assertNotEqual(updated_at, project.updated_at)

    def test_remove_comment(self):
        project = ProjectFactory(organizations=[self.organization])
        updated_at = project.updated_at
        self.client.force_authenticate(self.user)
        comment = CommentFactory(author=self.user, project=project)
        initial_count = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        self.client.delete(
            reverse(
                "Comment-detail",
                args=(project.id, comment.id),
            )
        )
        history = HistoricalProject.objects.filter(history_relation__id=project.id)
        latest_version = history.order_by("-history_date").first()
        response = self.client.get(
            reverse("Project-versions-detail", args=(project.id, latest_version.pk))
        )
        version = response.json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count(),
            initial_count + 1,
        )
        self.assertNotIn(comment.id, [c["id"] for c in version["comments"]])
        self.assertEqual(version["history_change_reason"], "Removed comment")
        project.refresh_from_db()
        self.assertNotEqual(updated_at, project.updated_at)

    def test_update_comment(self):
        project = ProjectFactory(organizations=[self.organization])
        updated_at = project.updated_at
        self.client.force_authenticate(self.user)
        comment = CommentFactory(author=self.user, project=project)
        initial_count = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        payload = {"content": faker.text()}
        self.client.patch(
            reverse(
                "Comment-detail",
                args=(project.id, comment.id),
            ),
            data=payload,
        )
        history = HistoricalProject.objects.filter(history_relation__id=project.id)
        latest_version = history.order_by("-history_date").first()
        response = self.client.get(
            reverse("Project-versions-detail", args=(project.id, latest_version.pk))
        )
        version = response.json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count(),
            initial_count + 1,
        )
        self.assertEqual(version["history_change_reason"], "Updated comment")
        self.assertIn(payload["content"], [c["content"] for c in version["comments"]])
        project.refresh_from_db()
        self.assertNotEqual(updated_at, project.updated_at)

    def test_add_linked_project(self):
        project = ProjectFactory(organizations=[self.organization])
        updated_at = project.updated_at
        to_link = ProjectFactory(organizations=[self.organization])
        self.client.force_authenticate(self.user)
        initial_count = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        payload = {
            "project_id": to_link.id,
            "reason": faker.sentence(),
            "target_id": project.id,
        }
        self.client.post(
            reverse("LinkedProjects-list", args=(project.id,)),
            data=payload,
        )
        history = HistoricalProject.objects.filter(history_relation__id=project.id)
        latest_version = history.order_by("-history_date").first()
        response = self.client.get(
            reverse("Project-versions-detail", args=(project.id, latest_version.pk))
        )
        version = response.json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count(),
            initial_count + 1,
        )
        self.assertIn(
            to_link.id, [p["project"]["id"] for p in version["linked_projects"]]
        )
        self.assertEqual(version["history_change_reason"], "Added linked project")
        project.refresh_from_db()
        self.assertNotEqual(updated_at, project.updated_at)

    def test_remove_linked_project(self):
        to_unlink = ProjectFactory(organizations=[self.organization])
        project = ProjectFactory(organizations=[self.organization])
        updated_at = project.updated_at
        linked_project = LinkedProjectFactory(project=to_unlink, target=project)
        self.client.force_authenticate(self.user)
        initial_count = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        self.client.delete(
            reverse("LinkedProjects-detail", args=(project.id, linked_project.id)),
        )
        history = HistoricalProject.objects.filter(history_relation__id=project.id)
        latest_version = history.order_by("-history_date").first()
        response = self.client.get(
            reverse("Project-versions-detail", args=(project.id, latest_version.pk))
        )
        version = response.json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count(),
            initial_count + 1,
        )
        self.assertNotIn(
            to_unlink.id, [p["project"]["id"] for p in version["linked_projects"]]
        )
        self.assertEqual(version["history_change_reason"], "Removed linked project")
        project.refresh_from_db()
        self.assertNotEqual(updated_at, project.updated_at)

    def test_update_linked_project(self):
        project = ProjectFactory(organizations=[self.organization])
        updated_at = project.updated_at
        linked_project = LinkedProjectFactory(target=project)
        self.client.force_authenticate(self.user)
        initial_count = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        payload = {"reason": faker.sentence()}
        self.client.patch(
            reverse("LinkedProjects-detail", args=(project.id, linked_project.id)),
            data=payload,
        )
        history = HistoricalProject.objects.filter(history_relation__id=project.id)
        latest_version = history.order_by("-history_date").first()
        response = self.client.get(
            reverse("Project-versions-detail", args=(project.id, latest_version.pk))
        )
        version = response.json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count(),
            initial_count + 1,
        )
        self.assertEqual(version["history_change_reason"], "Updated linked project")
        project.refresh_from_db()
        self.assertNotEqual(updated_at, project.updated_at)

    def test_add_many_linked_project(self):
        project = ProjectFactory(organizations=[self.organization])
        updated_at = project.updated_at
        to_link = ProjectFactory(organizations=[self.organization])
        self.client.force_authenticate(self.user)
        initial_count = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        payload = {
            "projects": [
                {
                    "project_id": to_link.id,
                    "reason": faker.sentence(),
                    "target_id": project.id,
                }
            ]
        }
        self.client.post(
            reverse("LinkedProjects-add-many", args=(project.id,)),
            data=payload,
        )
        history = HistoricalProject.objects.filter(history_relation__id=project.id)
        latest_version = history.order_by("-history_date").first()
        response = self.client.get(
            reverse("Project-versions-detail", args=(project.id, latest_version.pk))
        )
        version = response.json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count(),
            initial_count + 1,
        )
        self.assertIn(
            to_link.id, [p["project"]["id"] for p in version["linked_projects"]]
        )
        self.assertEqual(version["history_change_reason"], "Added linked project")
        project.refresh_from_db()
        self.assertNotEqual(updated_at, project.updated_at)

    def test_remove_many_linked_project(self):
        to_unlink = ProjectFactory(organizations=[self.organization])
        project = ProjectFactory(organizations=[self.organization])
        updated_at = project.updated_at
        LinkedProjectFactory(project=to_unlink, target=project)
        self.client.force_authenticate(self.user)
        initial_count = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        payload = {"project_ids": [to_unlink.id]}
        self.client.delete(
            reverse("LinkedProjects-delete-many", args=(project.id,)),
            data=payload,
        )
        history = HistoricalProject.objects.filter(history_relation__id=project.id)
        latest_version = history.order_by("-history_date").first()
        response = self.client.get(
            reverse("Project-versions-detail", args=(project.id, latest_version.pk))
        )
        version = response.json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count(),
            initial_count + 1,
        )
        self.assertNotIn(
            to_unlink.id, [p["project"]["id"] for p in version["linked_projects"]]
        )
        self.assertEqual(version["history_change_reason"], "Removed linked project")
        project.refresh_from_db()
        self.assertNotEqual(updated_at, project.updated_at)

    def test_update_title(self):
        project = ProjectFactory(organizations=[self.organization])
        updated_at = project.updated_at
        self.client.force_authenticate(self.user)
        initial_count = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        payload = {"title": faker.sentence()}
        self.client.patch(reverse("Project-detail", args=(project.id,)), data=payload)
        history = HistoricalProject.objects.filter(history_relation__id=project.id)
        latest_version = history.order_by("-history_date").first()
        response = self.client.get(
            reverse("Project-versions-detail", args=(project.id, latest_version.pk))
        )
        version = response.json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count(),
            initial_count + 1,
        )
        self.assertEqual(version["title"], payload["title"])
        self.assertEqual(version["history_change_reason"], "Updated: title")
        project.refresh_from_db()
        self.assertNotEqual(updated_at, project.updated_at)

    def test_update_purpose(self):
        project = ProjectFactory(organizations=[self.organization])
        updated_at = project.updated_at
        self.client.force_authenticate(self.user)
        initial_count = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        payload = {"purpose": faker.sentence()}
        self.client.patch(reverse("Project-detail", args=(project.id,)), data=payload)
        history = HistoricalProject.objects.filter(history_relation__id=project.id)
        latest_version = history.order_by("-history_date").first()
        response = self.client.get(
            reverse("Project-versions-detail", args=(project.id, latest_version.pk))
        )
        version = response.json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count(),
            initial_count + 1,
        )
        self.assertEqual(version["purpose"], payload["purpose"])
        self.assertEqual(version["history_change_reason"], "Updated: purpose")
        project.refresh_from_db()
        self.assertNotEqual(updated_at, project.updated_at)

    def test_update_purpose_and_title(self):
        project = ProjectFactory(organizations=[self.organization])
        updated_at = project.updated_at
        self.client.force_authenticate(self.user)
        initial_count = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        payload = {
            "title": faker.sentence(),
            "purpose": faker.sentence(),
        }
        self.client.patch(reverse("Project-detail", args=(project.id,)), data=payload)
        history = HistoricalProject.objects.filter(history_relation__id=project.id)
        latest_version = history.order_by("-history_date").first()
        response = self.client.get(
            reverse("Project-versions-detail", args=(project.id, latest_version.pk))
        )
        version = response.json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count(),
            initial_count + 1,
        )
        self.assertEqual(version["purpose"], payload["purpose"])
        self.assertEqual(version["title"], payload["title"])
        self.assertEqual(version["history_change_reason"], "Updated: title + purpose")
        project.refresh_from_db()
        self.assertNotEqual(updated_at, project.updated_at)

    def test_update_categories(self):
        organization = OrganizationFactory()
        pc1 = ProjectCategoryFactory(organization=organization)
        pc2 = ProjectCategoryFactory(organization=organization)
        project = ProjectFactory(categories=[pc1], organizations=[organization])
        updated_at = project.updated_at
        self.client.force_authenticate(self.user)
        initial_count = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        payload = {"project_categories_ids": [pc1.id, pc2.id]}
        self.client.patch(reverse("Project-detail", args=(project.id,)), data=payload)
        history = HistoricalProject.objects.filter(history_relation__id=project.id)
        latest_version = history.order_by("-history_date").first()
        response = self.client.get(
            reverse("Project-versions-detail", args=(project.id, latest_version.pk))
        )
        version = response.json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count(),
            initial_count + 1,
        )
        self.assertEqual(version["history_change_reason"], "Updated: categories")
        self.assertSetEqual(set(version["categories"]), {pc1.name, pc2.name})
        project.refresh_from_db()
        self.assertNotEqual(updated_at, project.updated_at)

    def test_update_tags(self):
        project = ProjectFactory(organizations=[self.organization])
        updated_at = project.updated_at
        self.client.force_authenticate(self.user)
        initial_count = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        tag = TagFactory()
        payload = {"tags": [tag.id]}
        self.client.patch(reverse("Project-detail", args=(project.id,)), data=payload)
        history = HistoricalProject.objects.filter(history_relation__id=project.id)
        latest_version = history.order_by("-history_date").first()
        response = self.client.get(
            reverse("Project-versions-detail", args=(project.id, latest_version.pk))
        )
        version = response.json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count(),
            initial_count + 1,
        )
        self.assertEqual(version["history_change_reason"], "Updated: tags")
        self.assertIn(tag.title, version["tags"])
        project.refresh_from_db()
        self.assertNotEqual(updated_at, project.updated_at)

    def test_add_blog_entry(self):
        project = ProjectFactory(organizations=[self.organization])
        updated_at = project.updated_at
        self.client.force_authenticate(self.user)
        initial_count = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        payload = {
            "title": faker.sentence(),
            "content": faker.text(),
            "project_id": project.id,
        }
        response = self.client.post(
            reverse("BlogEntry-list", args=(project.id,)), data=payload
        )
        history = HistoricalProject.objects.filter(history_relation__id=project.id)
        latest_version = history.order_by("-history_date").first()
        response = self.client.get(
            reverse("Project-versions-detail", args=(project.id, latest_version.pk))
        )
        version = response.json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count(),
            initial_count + 1,
        )
        self.assertEqual(version["history_change_reason"], "Added blog entry")
        project.refresh_from_db()
        self.assertNotEqual(updated_at, project.updated_at)

    def test_update_blog_entry(self):
        project = ProjectFactory(organizations=[self.organization])
        updated_at = project.updated_at
        blog_entry = BlogEntryFactory(project=project)
        self.client.force_authenticate(self.user)
        initial_count = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        payload = {
            "title": faker.sentence(),
        }
        self.client.patch(
            reverse("BlogEntry-detail", args=(project.id, blog_entry.id)),
            data=payload,
        )
        history = HistoricalProject.objects.filter(history_relation__id=project.id)
        latest_version = history.order_by("-history_date").first()
        response = self.client.get(
            reverse("Project-versions-detail", args=(project.id, latest_version.pk))
        )
        version = response.json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count(),
            initial_count + 1,
        )
        self.assertEqual(version["history_change_reason"], "Updated blog entry")
        project.refresh_from_db()
        self.assertNotEqual(updated_at, project.updated_at)

    def test_remove_blog_entry(self):
        project = ProjectFactory(organizations=[self.organization])
        updated_at = project.updated_at
        blog_entry = BlogEntryFactory(project=project)
        self.client.force_authenticate(self.user)
        initial_count = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        self.client.delete(
            reverse("BlogEntry-detail", args=(project.id, blog_entry.id)),
        )
        history = HistoricalProject.objects.filter(history_relation__id=project.id)
        latest_version = history.order_by("-history_date").first()
        response = self.client.get(
            reverse("Project-versions-detail", args=(project.id, latest_version.pk))
        )
        version = response.json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count(),
            initial_count + 1,
        )
        self.assertEqual(version["history_change_reason"], "Removed blog entry")
        project.refresh_from_db()
        self.assertNotEqual(updated_at, project.updated_at)

    def test_add_goal(self):
        project = ProjectFactory(organizations=[self.organization])
        updated_at = project.updated_at
        self.client.force_authenticate(self.user)
        initial_count = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        payload = {
            "title": faker.sentence(),
            "status": Goal.GoalStatus.ONGOING,
            "project_id": project.id,
        }
        response = self.client.post(
            reverse("Goal-list", args=(project.id,)), data=payload
        )
        history = HistoricalProject.objects.filter(history_relation__id=project.id)
        latest_version = history.order_by("-history_date").first()
        response = self.client.get(
            reverse("Project-versions-detail", args=(project.id, latest_version.pk))
        )
        version = response.json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count(),
            initial_count + 1,
        )
        self.assertEqual(version["history_change_reason"], "Added goal")
        project.refresh_from_db()
        self.assertNotEqual(updated_at, project.updated_at)

    def test_update_goal(self):
        project = ProjectFactory(organizations=[self.organization])
        updated_at = project.updated_at
        goal = GoalFactory(project=project)
        self.client.force_authenticate(self.user)
        initial_count = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        payload = {"title": faker.sentence()}
        self.client.patch(
            reverse("Goal-detail", args=(project.id, goal.id)),
            data=payload,
        )
        history = HistoricalProject.objects.filter(history_relation__id=project.id)
        latest_version = history.order_by("-history_date").first()
        response = self.client.get(
            reverse("Project-versions-detail", args=(project.id, latest_version.pk))
        )
        version = response.json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count(),
            initial_count + 1,
        )
        self.assertEqual(version["history_change_reason"], "Updated goal")
        project.refresh_from_db()
        self.assertNotEqual(updated_at, project.updated_at)

    def test_remove_goal(self):
        project = ProjectFactory(organizations=[self.organization])
        updated_at = project.updated_at
        goal = GoalFactory(project=project)
        self.client.force_authenticate(self.user)
        initial_count = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        self.client.delete(
            reverse("Goal-detail", args=(project.id, goal.id)),
        )
        history = HistoricalProject.objects.filter(history_relation__id=project.id)
        latest_version = history.order_by("-history_date").first()
        response = self.client.get(
            reverse("Project-versions-detail", args=(project.id, latest_version.pk))
        )
        version = response.json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count(),
            initial_count + 1,
        )
        self.assertEqual(version["history_change_reason"], "Removed goal")
        project.refresh_from_db()
        self.assertNotEqual(updated_at, project.updated_at)

    def test_add_location(self):
        project = ProjectFactory(organizations=[self.organization])
        updated_at = project.updated_at
        self.client.force_authenticate(self.user)
        initial_count = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        payload = {
            "title": faker.word(),
            "description": faker.text(),
            "lat": float(faker.latitude()),
            "lng": float(faker.longitude()),
            "type": Location.LocationType.TEAM,
            "project_id": project.id,
        }
        response = self.client.post(
            reverse("Location-list", args=(project.id,)), data=payload
        )
        history = HistoricalProject.objects.filter(history_relation__id=project.id)
        latest_version = history.order_by("-history_date").first()
        response = self.client.get(
            reverse("Project-versions-detail", args=(project.id, latest_version.pk))
        )
        version = response.json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count(),
            initial_count + 1,
        )
        self.assertEqual(version["history_change_reason"], "Added location")
        project.refresh_from_db()
        self.assertNotEqual(updated_at, project.updated_at)

    def test_update_location(self):
        project = ProjectFactory(organizations=[self.organization])
        updated_at = project.updated_at
        location = LocationFactory(project=project)
        self.client.force_authenticate(self.user)
        initial_count = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        payload = {"title": faker.word()}
        self.client.patch(
            reverse("Location-detail", args=(project.id, location.id)),
            data=payload,
        )
        history = HistoricalProject.objects.filter(history_relation__id=project.id)
        latest_version = history.order_by("-history_date").first()
        response = self.client.get(
            reverse("Project-versions-detail", args=(project.id, latest_version.pk))
        )
        version = response.json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count(),
            initial_count + 1,
        )
        self.assertEqual(version["history_change_reason"], "Updated location")
        project.refresh_from_db()
        self.assertNotEqual(updated_at, project.updated_at)

    def test_remove_location(self):
        project = ProjectFactory(organizations=[self.organization])
        updated_at = project.updated_at
        location = LocationFactory(project=project)
        self.client.force_authenticate(self.user)
        initial_count = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        self.client.delete(
            reverse("Location-detail", args=(project.id, location.id)),
        )
        history = HistoricalProject.objects.filter(history_relation__id=project.id)
        latest_version = history.order_by("-history_date").first()
        response = self.client.get(
            reverse("Project-versions-detail", args=(project.id, latest_version.pk))
        )
        version = response.json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count(),
            initial_count + 1,
        )
        self.assertEqual(version["history_change_reason"], "Removed location")
        project.refresh_from_db()
        self.assertNotEqual(updated_at, project.updated_at)

    @patch("apps.files.serializers.AttachmentLinkSerializer.get_url_response")
    def test_add_attachment_link(self, mocked):
        mocked_response = MockResponse()
        mocked.return_value = mocked_response
        project = ProjectFactory(organizations=[self.organization])
        updated_at = project.updated_at
        self.client.force_authenticate(self.user)
        initial_count = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        payload = {
            "site_url": faker.url(),
            "project_id": project.id,
        }
        response = self.client.post(
            reverse("AttachmentLink-list", args=(project.id,)), data=payload
        )
        history = HistoricalProject.objects.filter(history_relation__id=project.id)
        latest_version = history.order_by("-history_date").first()
        response = self.client.get(
            reverse("Project-versions-detail", args=(project.id, latest_version.pk))
        )
        version = response.json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count(),
            initial_count + 1,
        )
        self.assertEqual(version["history_change_reason"], "Added attachment link")
        project.refresh_from_db()
        self.assertNotEqual(updated_at, project.updated_at)

    @patch("apps.files.serializers.AttachmentLinkSerializer.get_url_response")
    def test_update_attachment_link(self, mocked):
        mocked_response = MockResponse()
        mocked.return_value = mocked_response
        project = ProjectFactory(organizations=[self.organization])
        updated_at = project.updated_at
        attachment_link = AttachmentLinkFactory(project=project)
        self.client.force_authenticate(self.user)
        initial_count = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        payload = {"site_url": faker.url()}
        self.client.patch(
            reverse("AttachmentLink-detail", args=(project.id, attachment_link.id)),
            data=payload,
        )
        history = HistoricalProject.objects.filter(history_relation__id=project.id)
        latest_version = history.order_by("-history_date").first()
        response = self.client.get(
            reverse("Project-versions-detail", args=(project.id, latest_version.pk))
        )
        version = response.json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count(),
            initial_count + 1,
        )
        self.assertEqual(version["history_change_reason"], "Updated attachment link")
        project.refresh_from_db()
        self.assertNotEqual(updated_at, project.updated_at)

    def test_remove_attachment_link(self):
        project = ProjectFactory(organizations=[self.organization])
        updated_at = project.updated_at
        attachment_link = AttachmentLinkFactory(project=project)
        self.client.force_authenticate(self.user)
        initial_count = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        self.client.delete(
            reverse("AttachmentLink-detail", args=(project.id, attachment_link.id)),
        )
        history = HistoricalProject.objects.filter(history_relation__id=project.id)
        latest_version = history.order_by("-history_date").first()
        response = self.client.get(
            reverse("Project-versions-detail", args=(project.id, latest_version.pk))
        )
        version = response.json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count(),
            initial_count + 1,
        )
        self.assertEqual(version["history_change_reason"], "Removed attachment link")
        project.refresh_from_db()
        self.assertNotEqual(updated_at, project.updated_at)

    def test_add_attachment_file(self):
        project = ProjectFactory(organizations=[self.organization])
        updated_at = project.updated_at
        self.client.force_authenticate(self.user)
        initial_count = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        payload = {
            "mime": "text/plain",
            "title": faker.text(max_nb_chars=50),
            "file": SimpleUploadedFile(
                "test_attachment_file.txt",
                b"test attachment file",
                content_type="text/plain",
            ),
            "attachment_type": AttachmentType.FILE,
            "project_id": project.id,
        }
        response = self.client.post(
            reverse("AttachmentFile-list", args=(project.id,)),
            data=payload,
            format="multipart",
        )
        history = HistoricalProject.objects.filter(history_relation__id=project.id)
        latest_version = history.order_by("-history_date").first()
        response = self.client.get(
            reverse("Project-versions-detail", args=(project.id, latest_version.pk))
        )
        version = response.json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count(),
            initial_count + 1,
        )
        self.assertEqual(version["history_change_reason"], "Added attachment file")
        project.refresh_from_db()
        self.assertNotEqual(updated_at, project.updated_at)

    def test_update_attachment_file(self):
        project = ProjectFactory(organizations=[self.organization])
        updated_at = project.updated_at
        attachment_file = AttachmentFileFactory(project=project)
        self.client.force_authenticate(self.user)
        initial_count = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        payload = {"title": faker.text(max_nb_chars=50)}
        response = self.client.patch(
            reverse("AttachmentFile-detail", args=(project.id, attachment_file.id)),
            data=payload,
            format="multipart",
        )
        history = HistoricalProject.objects.filter(history_relation__id=project.id)
        latest_version = history.order_by("-history_date").first()
        response = self.client.get(
            reverse("Project-versions-detail", args=(project.id, latest_version.pk))
        )
        version = response.json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count(),
            initial_count + 1,
        )
        self.assertEqual(version["history_change_reason"], "Updated attachment file")
        project.refresh_from_db()
        self.assertNotEqual(updated_at, project.updated_at)

    def test_remove_attachment_file(self):
        project = ProjectFactory(organizations=[self.organization])
        updated_at = project.updated_at
        attachment_file = AttachmentFileFactory(project=project)
        self.client.force_authenticate(self.user)
        initial_count = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        self.client.delete(
            reverse("AttachmentFile-detail", args=(project.id, attachment_file.id)),
        )
        history = HistoricalProject.objects.filter(history_relation__id=project.id)
        latest_version = history.order_by("-history_date").first()
        response = self.client.get(
            reverse("Project-versions-detail", args=(project.id, latest_version.pk))
        )
        version = response.json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count(),
            initial_count + 1,
        )
        self.assertEqual(version["history_change_reason"], "Removed attachment file")
        project.refresh_from_db()
        self.assertNotEqual(updated_at, project.updated_at)

    def test_add_announcement(self):
        project = ProjectFactory(organizations=[self.organization])
        updated_at = project.updated_at
        self.client.force_authenticate(self.user)
        initial_count = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        payload = {
            "title": faker.sentence(),
            "description": faker.text(),
            "type": Announcement.AnnouncementType.JOB,
            "is_remunerated": faker.boolean(),
            "project_id": project.id,
        }
        response = self.client.post(
            reverse("Announcement-list", args=(project.id,)),
            data=payload,
        )
        history = HistoricalProject.objects.filter(history_relation__id=project.id)
        latest_version = history.order_by("-history_date").first()
        response = self.client.get(
            reverse("Project-versions-detail", args=(project.id, latest_version.pk))
        )
        version = response.json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count(),
            initial_count + 1,
        )
        self.assertEqual(version["history_change_reason"], "Added announcement")
        project.refresh_from_db()
        self.assertNotEqual(updated_at, project.updated_at)

    def test_update_announcement(self):
        project = ProjectFactory(organizations=[self.organization])
        updated_at = project.updated_at
        announcement = AnnouncementFactory(project=project)
        self.client.force_authenticate(self.user)
        initial_count = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        payload = {"title": faker.sentence()}
        self.client.patch(
            reverse("Announcement-detail", args=(project.id, announcement.id)),
            data=payload,
        )
        history = HistoricalProject.objects.filter(history_relation__id=project.id)
        latest_version = history.order_by("-history_date").first()
        response = self.client.get(
            reverse("Project-versions-detail", args=(project.id, latest_version.pk))
        )
        version = response.json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count(),
            initial_count + 1,
        )
        self.assertEqual(version["history_change_reason"], "Updated announcement")
        project.refresh_from_db()
        self.assertNotEqual(updated_at, project.updated_at)

    def test_remove_announcement(self):
        project = ProjectFactory(organizations=[self.organization])
        updated_at = project.updated_at
        announcement = AnnouncementFactory(project=project)
        self.client.force_authenticate(self.user)
        initial_count = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        self.client.delete(
            reverse("Announcement-detail", args=(project.id, announcement.id)),
        )
        history = HistoricalProject.objects.filter(history_relation__id=project.id)
        latest_version = history.order_by("-history_date").first()
        response = self.client.get(
            reverse("Project-versions-detail", args=(project.id, latest_version.pk))
        )
        version = response.json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count(),
            initial_count + 1,
        )
        self.assertEqual(version["history_change_reason"], "Removed announcement")
        project.refresh_from_db()
        self.assertNotEqual(updated_at, project.updated_at)
