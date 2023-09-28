from unittest.mock import patch

from django.apps import apps
from django.urls import reverse

from apps.accounts.factories import UserFactory
from apps.commons.test import JwtAPITestCase
from apps.commons.test.testcases import TagTestCase
from apps.feedbacks.factories import CommentFactory
from apps.misc.factories import TagFactory
from apps.organizations.factories import OrganizationFactory, ProjectCategoryFactory
from apps.projects.factories import LinkedProjectFactory, ProjectFactory
from apps.projects.models import Project

HistoricalProject = apps.get_model("projects", "HistoricalProject")


class ProjectHistoryTestCase(JwtAPITestCase, TagTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.test_image = cls.get_test_image()

    def test_create_project(self):
        owner = UserFactory()
        self.client.force_authenticate(owner)
        organization = OrganizationFactory()
        fake = ProjectFactory.build(header_image=self.test_image)
        pc = ProjectCategoryFactory(organization=organization)
        payload = {
            "title": fake.title,
            "description": fake.description,
            "header_image_id": fake.header_image.id,
            "is_locked": fake.is_locked,
            "is_shareable": fake.is_shareable,
            "purpose": fake.purpose,
            "language": fake.language,
            "publication_status": fake.publication_status,
            "life_status": fake.life_status,
            "sdgs": fake.sdgs,
            "project_categories_ids": [pc.id],
            "organizations_codes": [organization.code],
        }
        response = self.client.post(reverse("Project-list"), data=payload)
        project_id = response.json()["id"]
        history = HistoricalProject.objects.filter(history_relation__id=project_id)
        latest_version = max(history, key=lambda x: x.history_date)
        response = self.client.get(
            reverse("Project-versions-detail", args=(project_id, latest_version.pk))
        )
        version = response.json()
        assert response.status_code == 200
        assert version["history_change_reason"] == "Created project"
        assert owner.get_full_name() in version["members"]

    def test_add_project_member(self):
        project = ProjectFactory()
        self.client.force_authenticate(
            UserFactory(permissions=[("projects.change_project", project)])
        )
        initial = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        user = UserFactory()
        payload = {
            Project.DefaultGroup.MEMBERS: [user.keycloak_id],
        }
        self.client.post(
            reverse("Project-add-member", args=[project.id]),
            data=payload,
        )
        history = HistoricalProject.objects.filter(history_relation__id=project.id)
        latest_version = max(history, key=lambda x: x.history_date)
        response = self.client.get(
            reverse("Project-versions-detail", args=(project.id, latest_version.pk))
        )
        new_count = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        assert response.status_code == 200
        assert new_count == initial + 1
        assert user in project.get_all_members()
        assert response.data["history_change_reason"] == "Added members"

    def test_remove_project_member(self):
        project = ProjectFactory()
        self.client.force_authenticate(
            UserFactory(permissions=[("projects.change_project", project)])
        )
        initial = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )

        to_delete = UserFactory()
        project.members.add(to_delete)
        payload = {
            "users": [to_delete.keycloak_id],
        }
        self.client.post(
            reverse("Project-remove-member", args=[project.id]),
            data=payload,
        )
        history = HistoricalProject.objects.filter(history_relation__id=project.id)
        latest_version = max(history, key=lambda x: x.history_date)
        response = self.client.get(
            reverse("Project-versions-detail", args=(project.id, latest_version.pk))
        )
        version = response.json()
        new_count = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        assert response.status_code == 200
        assert new_count == initial + 1
        assert to_delete.get_full_name() not in version["members"]
        assert version["history_change_reason"] == "Removed members"

    def test_add_comment(self):
        project = ProjectFactory()
        self.client.force_authenticate(UserFactory())
        initial = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        payload = {
            "project_id": project.id,
            "content": "content",
        }
        response = self.client.post(
            reverse("Comment-list", kwargs={"project_id": project.id}), data=payload
        )
        comment_id = response.json()["id"]
        history = HistoricalProject.objects.filter(history_relation__id=project.id)
        latest_version = max(history, key=lambda x: x.history_date)
        response = self.client.get(
            reverse("Project-versions-detail", args=(project.id, latest_version.pk))
        )
        version = response.json()
        new_count = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        assert response.status_code == 200
        assert new_count == initial + 1
        assert comment_id in [c["id"] for c in version["comments"]]
        assert version["history_change_reason"] == "Added comment"

    def test_remove_comment(self):
        user = UserFactory()
        comment = CommentFactory(author=user)
        project = comment.project
        self.client.force_authenticate(user)
        initial = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )

        self.client.delete(
            reverse(
                "Comment-detail", kwargs={"id": comment.id, "project_id": project.id}
            )
        )
        history = HistoricalProject.objects.filter(history_relation__id=project.id)
        latest_version = max(history, key=lambda x: x.history_date)
        response = self.client.get(
            reverse("Project-versions-detail", args=(project.id, latest_version.pk))
        )
        version = response.json()
        new_count = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        assert response.status_code == 200
        assert new_count == initial + 1
        assert comment.id not in [c["id"] for c in version["comments"]]
        assert version["history_change_reason"] == "Deleted comment"

    def test_update_comment(self):
        user = UserFactory()
        comment = CommentFactory(author=user)
        project = comment.project
        self.client.force_authenticate(user)
        initial = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        payload = {"content": "NewContent"}
        self.client.patch(
            reverse(
                "Comment-detail", kwargs={"id": comment.id, "project_id": project.id}
            ),
            payload,
        )
        history = HistoricalProject.objects.filter(history_relation__id=project.id)
        latest_version = max(history, key=lambda x: x.history_date)
        response = self.client.get(
            reverse("Project-versions-detail", args=(project.id, latest_version.pk))
        )
        version = response.json()
        new_count = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        assert response.status_code == 200
        assert new_count == initial + 1
        assert version["history_change_reason"] == "Updated comment"
        assert payload["content"] in [c["content"] for c in version["comments"]]

    def test_add_linked_project(self):
        project = ProjectFactory()
        to_link = ProjectFactory()
        self.client.force_authenticate(
            UserFactory(permissions=[("projects.change_project", project)])
        )
        initial = (
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
        latest_version = max(history, key=lambda x: x.history_date)
        response = self.client.get(
            reverse("Project-versions-detail", args=(project.id, latest_version.pk))
        )
        version = response.json()
        new_count = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        assert response.status_code == 200
        assert new_count == initial + 1
        assert to_link.id in [p["project"]["id"] for p in version["linked_projects"]]
        assert version["history_change_reason"] == "Added linked projects"

    def test_remove_linked_project(self):
        to_unlink = ProjectFactory()
        project = ProjectFactory()
        linked_project = LinkedProjectFactory(project=to_unlink, target=project)
        self.client.force_authenticate(
            UserFactory(permissions=[("projects.change_project", project)])
        )
        initial = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )

        self.client.delete(
            reverse("LinkedProjects-detail", args=(project.id, linked_project.id)),
        )

        history = HistoricalProject.objects.filter(history_relation__id=project.id)
        latest_version = max(history, key=lambda x: x.history_date)
        response = self.client.get(
            reverse("Project-versions-detail", args=(project.id, latest_version.pk))
        )
        version = response.json()
        new_count = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        assert response.status_code == 200
        assert new_count == initial + 1
        assert to_unlink.id not in [
            p["project"]["id"] for p in version["linked_projects"]
        ]
        assert version["history_change_reason"] == "Removed linked projects"

    def test_update_linked_project(self):
        project = ProjectFactory()
        linked_project = LinkedProjectFactory(target=project)
        self.client.force_authenticate(
            UserFactory(permissions=[("projects.change_project", project)])
        )
        initial = (
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
        latest_version = max(history, key=lambda x: x.history_date)
        response = self.client.get(
            reverse("Project-versions-detail", args=(project.id, latest_version.pk))
        )
        version = response.json()
        new_count = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        assert response.status_code == 200
        assert new_count == initial + 1
        assert version["history_change_reason"] == "Updated linked projects"

    def test_add_many_linked_project(self):
        project = ProjectFactory()
        to_link = ProjectFactory()
        self.client.force_authenticate(
            UserFactory(permissions=[("projects.change_project", project)])
        )
        initial = (
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
        latest_version = max(history, key=lambda x: x.history_date)
        response = self.client.get(
            reverse("Project-versions-detail", args=(project.id, latest_version.pk))
        )
        version = response.json()
        new_count = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        assert response.status_code == 200
        assert new_count == initial + 1
        assert to_link.id in [p["project"]["id"] for p in version["linked_projects"]]
        assert version["history_change_reason"] == "Added linked projects"

    def test_remove_many_linked_project(self):
        to_unlink = ProjectFactory()
        project = ProjectFactory()
        LinkedProjectFactory(project=to_unlink, target=project)
        self.client.force_authenticate(
            UserFactory(permissions=[("projects.change_project", project)])
        )
        initial = (
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
        latest_version = max(history, key=lambda x: x.history_date)
        response = self.client.get(
            reverse("Project-versions-detail", args=(project.id, latest_version.pk))
        )
        version = response.json()
        new_count = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        assert response.status_code == 200
        assert new_count == initial + 1
        assert to_unlink.id not in [
            p["project"]["id"] for p in version["linked_projects"]
        ]
        assert version["history_change_reason"] == "Removed linked projects"

    def test_update_title(self):
        project = ProjectFactory()
        self.client.force_authenticate(
            UserFactory(permissions=[("projects.change_project", project)])
        )
        initial = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        payload = {"title": "New title"}
        self.client.patch(reverse("Project-detail", args=(project.id,)), data=payload)
        history = HistoricalProject.objects.filter(history_relation__id=project.id)
        latest_version = max(history, key=lambda x: x.history_date)
        response = self.client.get(
            reverse("Project-versions-detail", args=(project.id, latest_version.pk))
        )
        version = response.json()
        new_count = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        assert response.status_code == 200
        assert new_count == initial + 1
        assert version["title"] == "New title"
        assert version["history_change_reason"] == "Updated: title"

    def test_update_purpose(self):
        project = ProjectFactory()
        self.client.force_authenticate(
            UserFactory(permissions=[("projects.change_project", project)])
        )
        initial = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        payload = {"purpose": "New purpose"}
        self.client.patch(reverse("Project-detail", args=(project.id,)), data=payload)
        history = HistoricalProject.objects.filter(history_relation__id=project.id)
        latest_version = max(history, key=lambda x: x.history_date)
        response = self.client.get(
            reverse("Project-versions-detail", args=(project.id, latest_version.pk))
        )
        version = response.json()
        new_count = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        assert response.status_code == 200
        assert new_count == initial + 1
        assert version["purpose"] == "New purpose"
        assert version["history_change_reason"] == "Updated: purpose"

    def test_update_purpose_and_title(self):
        project = ProjectFactory()
        self.client.force_authenticate(
            UserFactory(permissions=[("projects.change_project", project)])
        )
        initial = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        payload = {"title": "New title", "purpose": "New purpose"}
        self.client.patch(reverse("Project-detail", args=(project.id,)), data=payload)
        history = HistoricalProject.objects.filter(history_relation__id=project.id)
        latest_version = max(history, key=lambda x: x.history_date)
        response = self.client.get(
            reverse("Project-versions-detail", args=(project.id, latest_version.pk))
        )
        version = response.json()
        new_count = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        assert response.status_code == 200
        assert new_count == initial + 1
        assert version["purpose"] == "New purpose"
        assert version["title"] == "New title"
        assert version["history_change_reason"] == "Updated: title + purpose"

    def test_update_categories(self):
        organization = OrganizationFactory()
        pc1 = ProjectCategoryFactory(organization=organization)
        pc2 = ProjectCategoryFactory(organization=organization)
        project = ProjectFactory(categories=[pc1], organizations=[organization])
        self.client.force_authenticate(
            UserFactory(permissions=[("projects.change_project", project)])
        )
        initial = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        payload = {"project_categories_ids": [pc1.id, pc2.id]}
        self.client.patch(reverse("Project-detail", args=(project.id,)), data=payload)
        history = HistoricalProject.objects.filter(history_relation__id=project.id)
        latest_version = max(history, key=lambda x: x.history_date)
        response = self.client.get(
            reverse("Project-versions-detail", args=(project.id, latest_version.pk))
        )
        version = response.json()
        new_count = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        assert response.status_code == 200
        assert new_count == initial + 1
        assert version["history_change_reason"] == "Updated: categories"
        assert set(version["categories"]) == {pc1.name, pc2.name}
        assert version["main_category"] == pc1.name

    def test_update_main_category(self):
        organization = OrganizationFactory()
        pc1 = ProjectCategoryFactory(organization=organization)
        pc2 = ProjectCategoryFactory(organization=organization)
        project = ProjectFactory(categories=[pc1], organizations=[organization])
        self.client.force_authenticate(
            UserFactory(permissions=[("projects.change_project", project)])
        )
        initial = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        payload = {"project_categories_ids": [pc2.id]}
        self.client.patch(reverse("Project-detail", args=(project.id,)), data=payload)
        history = HistoricalProject.objects.filter(history_relation__id=project.id)
        latest_version = max(history, key=lambda x: x.history_date)
        response = self.client.get(
            reverse("Project-versions-detail", args=(project.id, latest_version.pk))
        )
        version = response.json()
        new_count = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        assert response.status_code == 200
        assert new_count == initial + 1
        assert version["history_change_reason"] == "Updated: categories"
        assert version["categories"] == [pc2.name]
        assert version["main_category"] == pc2.name

    @patch(target="apps.misc.api.get_tag_from_wikipedia_gw")
    def test_update_wikipedia_tags(self, mocked):
        mocked.side_effect = self.side_effect
        project = ProjectFactory()
        self.client.force_authenticate(
            UserFactory(permissions=[("projects.change_project", project)])
        )
        initial = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        payload = {"wikipedia_tags_ids": ["Q1735684"]}
        self.client.patch(reverse("Project-detail", args=(project.id,)), data=payload)
        history = HistoricalProject.objects.filter(history_relation__id=project.id)
        latest_version = max(history, key=lambda x: x.history_date)
        response = self.client.get(
            reverse("Project-versions-detail", args=(project.id, latest_version.pk))
        )
        version = response.json()
        new_count = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        assert response.status_code == 200
        assert new_count == initial + 1
        assert version["history_change_reason"] == "Updated: wikipedia_tags"
        assert "Kate Foo Kune en" in version["wikipedia_tags"]

    def test_update_organization_tags(self):
        organization = OrganizationFactory()
        tag = TagFactory(organization=organization)
        project = ProjectFactory(organizations=[organization])
        self.client.force_authenticate(
            UserFactory(permissions=[("projects.change_project", project)])
        )
        initial = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        payload = {"organization_tags_ids": [tag.id]}
        self.client.patch(reverse("Project-detail", args=(project.id,)), data=payload)
        history = HistoricalProject.objects.filter(history_relation__id=project.id)
        latest_version = max(history, key=lambda x: x.history_date)
        response = self.client.get(
            reverse("Project-versions-detail", args=(project.id, latest_version.pk))
        )
        version = response.json()
        new_count = (
            HistoricalProject.objects.filter(id=project.id)
            .exclude(history_change_reason=None)
            .count()
        )
        assert response.status_code == 200
        assert new_count == initial + 1
        assert version["history_change_reason"] == "Updated: organization_tags"
        assert tag.name in version["organization_tags"]
