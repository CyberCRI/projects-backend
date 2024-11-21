from django.apps import apps
from django.urls import reverse
from faker import Faker
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase
from apps.feedbacks.factories import CommentFactory
from apps.organizations.factories import OrganizationFactory, ProjectCategoryFactory
from apps.projects.factories import LinkedProjectFactory, ProjectFactory
from apps.projects.models import Project
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
        self.client.force_authenticate(self.user)
        initial_count = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        payload = {
            Project.DefaultGroup.MEMBERS: [self.user.id],
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

    def test_remove_project_member(self):

        project = ProjectFactory(organizations=[self.organization], with_owner=True)
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

    def test_add_comment(self):
        project = ProjectFactory(organizations=[self.organization])
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

    def test_remove_comment(self):
        project = ProjectFactory(organizations=[self.organization])
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
        self.assertEqual(version["history_change_reason"], "Deleted comment")

    def test_update_comment(self):
        project = ProjectFactory(organizations=[self.organization])
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

    def test_add_linked_project(self):
        project = ProjectFactory(organizations=[self.organization])
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
        self.assertEqual(version["history_change_reason"], "Added linked projects")

    def test_remove_linked_project(self):
        to_unlink = ProjectFactory(organizations=[self.organization])
        project = ProjectFactory(organizations=[self.organization])
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
        self.assertEqual(version["history_change_reason"], "Removed linked projects")

    def test_update_linked_project(self):
        project = ProjectFactory(organizations=[self.organization])
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
        self.assertEqual(version["history_change_reason"], "Updated linked projects")

    def test_add_many_linked_project(self):
        project = ProjectFactory(organizations=[self.organization])
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
        self.assertEqual(version["history_change_reason"], "Added linked projects")

    def test_remove_many_linked_project(self):
        to_unlink = ProjectFactory(organizations=[self.organization])
        project = ProjectFactory(organizations=[self.organization])
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
        self.assertEqual(version["history_change_reason"], "Removed linked projects")

    def test_update_title(self):
        project = ProjectFactory(organizations=[self.organization])
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

    def test_update_purpose(self):
        project = ProjectFactory(organizations=[self.organization])
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

    def test_update_purpose_and_title(self):
        project = ProjectFactory(organizations=[self.organization])
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

    def test_update_categories(self):
        organization = OrganizationFactory()
        pc1 = ProjectCategoryFactory(organization=organization)
        pc2 = ProjectCategoryFactory(organization=organization)
        project = ProjectFactory(categories=[pc1], organizations=[organization])
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
        self.assertEqual(version["main_category"], pc1.name)

    def test_update_main_category(self):
        organization = OrganizationFactory()
        pc1 = ProjectCategoryFactory(organization=organization)
        pc2 = ProjectCategoryFactory(organization=organization)
        project = ProjectFactory(categories=[pc1], organizations=[organization])
        self.client.force_authenticate(self.user)
        initial_count = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        payload = {"project_categories_ids": [pc2.id]}
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
        self.assertEqual(version["categories"], [pc2.name])
        self.assertEqual(version["main_category"], pc2.name)

    def test_update_tags(self):
        project = ProjectFactory(organizations=[self.organization])
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
