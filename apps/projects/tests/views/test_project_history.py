from unittest.mock import patch

from django.apps import apps
from django.urls import reverse
from faker import Faker

from apps.accounts.factories import UserFactory
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase
from apps.commons.test.testcases import TagTestCase
from apps.feedbacks.factories import CommentFactory
from apps.misc.factories import TagFactory
from apps.organizations.factories import OrganizationFactory, ProjectCategoryFactory
from apps.projects.factories import LinkedProjectFactory, ProjectFactory
from apps.projects.models import Project

faker = Faker()

HistoricalProject = apps.get_model("projects", "HistoricalProject")


class ProjectHistoryTestCase(JwtAPITestCase, TagTestCase):
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
        assert response.status_code == 200
        assert version["history_change_reason"] == "Created project"
        assert self.user.get_full_name() in version["members"]

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
        assert response.status_code == 200
        assert (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        ) == initial_count + 1
        assert response.data["history_change_reason"] == "Added members"

    def test_remove_project_member(self):
        project = ProjectFactory(organizations=[self.organization])
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
        assert response.status_code == 200
        assert (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        ) == initial_count + 1
        assert self.user.get_full_name() not in version["members"]
        assert version["history_change_reason"] == "Removed members"

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
            "content": "content",
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
        assert response.status_code == 200
        assert (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        ) == initial_count + 1
        assert comment_id in [c["id"] for c in version["comments"]]
        assert version["history_change_reason"] == "Added comment"

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
        assert response.status_code == 200
        assert (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        ) == initial_count + 1
        assert comment.id not in [c["id"] for c in version["comments"]]
        assert version["history_change_reason"] == "Deleted comment"

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
        assert response.status_code == 200
        assert (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        ) == initial_count + 1
        assert version["history_change_reason"] == "Updated comment"
        assert payload["content"] in [c["content"] for c in version["comments"]]

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
            "reason": "reason",
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
        assert response.status_code == 200
        assert (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        ) == initial_count + 1
        assert to_link.id in [p["project"]["id"] for p in version["linked_projects"]]
        assert version["history_change_reason"] == "Added linked projects"

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
        assert response.status_code == 200
        assert (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        ) == initial_count + 1
        assert to_unlink.id not in [
            p["project"]["id"] for p in version["linked_projects"]
        ]
        assert version["history_change_reason"] == "Removed linked projects"

    def test_update_linked_project(self):
        project = ProjectFactory(organizations=[self.organization])
        linked_project = LinkedProjectFactory(target=project)
        self.client.force_authenticate(self.user)
        initial_count = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        payload = {"reason": "new reason"}
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
        assert response.status_code == 200
        assert (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        ) == initial_count + 1
        assert version["history_change_reason"] == "Updated linked projects"

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
                {"project_id": to_link.id, "reason": "reason", "target_id": project.id}
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
        assert response.status_code == 200
        assert (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        ) == initial_count + 1
        assert to_link.id in [p["project"]["id"] for p in version["linked_projects"]]
        assert version["history_change_reason"] == "Added linked projects"

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
        assert response.status_code == 200
        assert (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        ) == initial_count + 1
        assert to_unlink.id not in [
            p["project"]["id"] for p in version["linked_projects"]
        ]
        assert version["history_change_reason"] == "Removed linked projects"

    def test_update_title(self):
        project = ProjectFactory(organizations=[self.organization])
        self.client.force_authenticate(self.user)
        initial_count = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        payload = {"title": "New title"}
        self.client.patch(reverse("Project-detail", args=(project.id,)), data=payload)
        history = HistoricalProject.objects.filter(history_relation__id=project.id)
        latest_version = history.order_by("-history_date").first()
        response = self.client.get(
            reverse("Project-versions-detail", args=(project.id, latest_version.pk))
        )
        version = response.json()
        assert response.status_code == 200
        assert (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        ) == initial_count + 1
        assert version["title"] == "New title"
        assert version["history_change_reason"] == "Updated: title"

    def test_update_purpose(self):
        project = ProjectFactory(organizations=[self.organization])
        self.client.force_authenticate(self.user)
        initial_count = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        payload = {"purpose": "New purpose"}
        self.client.patch(reverse("Project-detail", args=(project.id,)), data=payload)
        history = HistoricalProject.objects.filter(history_relation__id=project.id)
        latest_version = history.order_by("-history_date").first()
        response = self.client.get(
            reverse("Project-versions-detail", args=(project.id, latest_version.pk))
        )
        version = response.json()
        assert response.status_code == 200
        assert (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        ) == initial_count + 1
        assert version["purpose"] == "New purpose"
        assert version["history_change_reason"] == "Updated: purpose"

    def test_update_purpose_and_title(self):
        project = ProjectFactory(organizations=[self.organization])
        self.client.force_authenticate(self.user)
        initial_count = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        payload = {"title": "New title", "purpose": "New purpose"}
        self.client.patch(reverse("Project-detail", args=(project.id,)), data=payload)
        history = HistoricalProject.objects.filter(history_relation__id=project.id)
        latest_version = history.order_by("-history_date").first()
        response = self.client.get(
            reverse("Project-versions-detail", args=(project.id, latest_version.pk))
        )
        version = response.json()
        assert response.status_code == 200
        assert (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        ) == initial_count + 1
        assert version["purpose"] == "New purpose"
        assert version["title"] == "New title"
        assert version["history_change_reason"] == "Updated: title + purpose"

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
        assert response.status_code == 200
        assert (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        ) == initial_count + 1
        assert version["history_change_reason"] == "Updated: categories"
        assert set(version["categories"]) == {pc1.name, pc2.name}
        assert version["main_category"] == pc1.name

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
        assert response.status_code == 200
        assert (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        ) == initial_count + 1
        assert version["history_change_reason"] == "Updated: categories"
        assert version["categories"] == [pc2.name]
        assert version["main_category"] == pc2.name

    @patch(target="apps.misc.api.get_tag_from_wikipedia_gw")
    def test_update_wikipedia_tags(self, mocked):
        mocked.side_effect = self.side_effect
        project = ProjectFactory(organizations=[self.organization])
        self.client.force_authenticate(self.user)
        initial_count = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        payload = {"wikipedia_tags_ids": ["Q1735684"]}
        self.client.patch(reverse("Project-detail", args=(project.id,)), data=payload)
        history = HistoricalProject.objects.filter(history_relation__id=project.id)
        latest_version = history.order_by("-history_date").first()
        response = self.client.get(
            reverse("Project-versions-detail", args=(project.id, latest_version.pk))
        )
        version = response.json()
        assert response.status_code == 200
        assert (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        ) == initial_count + 1
        assert version["history_change_reason"] == "Updated: wikipedia_tags"
        assert "Kate Foo Kune en" in version["wikipedia_tags"]

    def test_update_organization_tags(self):
        organization = OrganizationFactory()
        tag = TagFactory(organization=organization)
        project = ProjectFactory(organizations=[organization])
        self.client.force_authenticate(self.user)
        initial_count = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        payload = {"organization_tags_ids": [tag.id]}
        self.client.patch(reverse("Project-detail", args=(project.id,)), data=payload)
        history = HistoricalProject.objects.filter(history_relation__id=project.id)
        latest_version = history.order_by("-history_date").first()
        response = self.client.get(
            reverse("Project-versions-detail", args=(project.id, latest_version.pk))
        )
        version = response.json()
        assert response.status_code == 200
        assert (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        ) == initial_count + 1
        assert version["history_change_reason"] == "Updated: organization_tags"
        assert tag.name in version["organization_tags"]
