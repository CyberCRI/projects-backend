import datetime
import random
from typing import Dict
from unittest.mock import patch

from django.test.client import BOUNDARY, MULTIPART_CONTENT, encode_multipart
from django.urls import reverse
from django.utils.timezone import make_aware, now
from rest_framework import status

from apps.accounts.factories import PeopleGroupFactory, UserFactory
from apps.accounts.utils import get_superadmins_group
from apps.announcements.factories import AnnouncementFactory
from apps.commons.test import JwtAPITestCase
from apps.commons.test.testcases import TagTestCase
from apps.feedbacks.factories import FollowFactory, ReviewFactory
from apps.files.factories import AttachmentFileFactory, AttachmentLinkFactory
from apps.goals.factories import GoalFactory
from apps.misc.factories import TagFactory, WikipediaTagFactory
from apps.organizations.factories import OrganizationFactory, ProjectCategoryFactory
from apps.projects.factories import (
    BlogEntryFactory,
    LinkedProjectFactory,
    LocationFactory,
    ProjectFactory,
)
from apps.projects.models import LinkedProject, Project
from apps.projects.serializers import BlogEntrySerializer


class ProjectJwtAPITestCase(JwtAPITestCase):
    def create_payload(self):
        fake = ProjectFactory.build()
        organization = OrganizationFactory()
        category = ProjectCategoryFactory(organization=organization)
        image = self.get_test_image()
        organization_tags = TagFactory.create_batch(3, organization=organization)
        return {
            "organizations_codes": [organization.code],
            "title": fake.title,
            "description": fake.description,
            "header_image_id": image.id,
            "is_shareable": fake.is_shareable,
            "purpose": fake.purpose,
            "language": fake.language,
            "publication_status": fake.publication_status,
            "life_status": fake.life_status,
            "sdgs": fake.sdgs,
            "project_categories_ids": [category.id],
            "wikipedia_tags_ids": ["Q1735684"],
            "organization_tags_ids": [t.id for t in organization_tags],
            "images_ids": [],
        }

    def create_partial_payload(self):
        return {"title": "New title"}

    def assert_project_eq_content(
        self, project: Project, content: Dict, duplicate=False, blog_entries=None
    ):
        self.assertEqual(project.title, content["title"])
        self.assertEqual(project.description, content["description"])
        self.assertEqual(project.is_shareable, content["is_shareable"])
        self.assertEqual(project.purpose, content["purpose"])
        self.assertEqual(project.language, content["language"])
        self.assertEqual(project.publication_status, content["publication_status"])
        self.assertEqual(project.life_status, content["life_status"])
        self.assertEqual(project.sdgs, content["sdgs"])
        self.assertEqual(
            set(project.categories.all().values_list("id", flat=True)),
            set([c["id"] for c in content["categories"]]),
        )
        self.assertEqual(
            set(project.wikipedia_tags.all().values_list("wikipedia_qid", flat=True)),
            set([t["wikipedia_qid"] for t in content["wikipedia_tags"]]),
        )
        self.assertEqual(
            set(project.organization_tags.all().values_list("id", flat=True)),
            set([t["id"] for t in content["organization_tags"]]),
        )
        self.assertEqual(
            set(project.images.all().values_list("id", flat=True)),
            set([s["id"] for s in content["images"]]),
        )
        self.assertEqual(
            set(project.linked_projects.all().values_list("id", flat=True)),
            set([s["id"] for s in content["linked_projects"]]),
        )

        if blog_entries:
            self.assertEqual(
                BlogEntrySerializer(blog_entries, many=True).data,
                content["blog_entries"],
            )


class ProjectTestCaseAnonymous(ProjectJwtAPITestCase, TagTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.test_image = cls.get_test_image()

    @patch(target="apps.misc.api.get_tag_from_wikipedia_gw")
    def test_create_anonymous(self, mocked):
        mocked.side_effect = self.side_effect
        payload = self.create_payload()
        response = self.client.post(reverse("Project-list"), data=payload)
        self.assertEqual(
            response.status_code, status.HTTP_401_UNAUTHORIZED, response.json()
        )

    def test_destroy_anonymous(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        response = self.client.delete(reverse("Project-detail", args=(project.id,)))
        self.assertEqual(
            response.status_code, status.HTTP_401_UNAUTHORIZED, response.json()
        )

    @patch(target="apps.misc.api.get_tag_from_wikipedia_gw")
    def test_update_anonymous(self, mocked):
        mocked.side_effect = self.side_effect
        pc = ProjectCategoryFactory(background_image=self.test_image)
        project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC, categories=[pc]
        )
        organization_tags = TagFactory.create_batch(
            3, organization=project.organizations.first()
        )
        payload = {
            "title": project.title,
            "description": project.description,
            "is_shareable": project.is_shareable,
            "purpose": project.purpose,
            "language": project.language,
            "publication_status": project.publication_status,
            "life_status": project.life_status,
            "sdgs": project.sdgs,
            "project_categories_ids": [pc.id],
            "organizations_codes": list(
                project.organizations.values_list("code", flat=True)
            ),
            "wikipedia_tags_ids": ["Q1735684"],
            "organization_tags_ids": [t.id for t in organization_tags],
        }
        response = self.client.put(
            reverse("Project-detail", args=(project.id,)), data=payload
        )
        self.assertEqual(
            response.status_code, status.HTTP_401_UNAUTHORIZED, response.json()
        )

    def test_partial_update_anonymous(self):
        pc = ProjectCategoryFactory(background_image=self.test_image)
        project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC, categories=[pc]
        )
        payload = {"title": "NewTitle"}
        response = self.client.patch(
            reverse("Project-detail", args=(project.id,)), data=payload
        )
        self.assertEqual(
            response.status_code, status.HTTP_401_UNAUTHORIZED, response.json()
        )

    def test_duplicate_anonymous(self):
        pc = ProjectCategoryFactory(background_image=self.test_image)
        project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC, categories=[pc]
        )
        response = self.client.post(reverse("Project-duplicate", args=(project.id,)))
        self.assertEqual(
            response.status_code, status.HTTP_401_UNAUTHORIZED, response.json()
        )

    def test_add_members_anonymous(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        project.members.add(UserFactory())

        member = UserFactory()
        payload = {
            Project.DefaultGroup.MEMBERS: [member.keycloak_id],
        }
        response = self.client.post(
            reverse("Project-add-member", args=(project.id,)), data=payload
        )
        self.assertEqual(
            response.status_code, status.HTTP_401_UNAUTHORIZED, response.json()
        )

    def test_remove_members_anonymous(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        to_delete = UserFactory()
        project.members.add(UserFactory(), to_delete)

        payload = {"users": [to_delete.keycloak_id]}
        response = self.client.post(
            reverse("Project-remove-member", args=[project.id]), data=payload
        )
        self.assertEqual(
            response.status_code, status.HTTP_401_UNAUTHORIZED, response.json()
        )

    def test_add_groups_anonymous(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        project.member_people_groups.add(PeopleGroupFactory())

        member_group = PeopleGroupFactory()
        payload = {
            Project.DefaultGroup.PEOPLE_GROUPS: [member_group.id],
        }
        response = self.client.post(
            reverse("Project-add-member", args=(project.id,)), data=payload
        )
        self.assertEqual(
            response.status_code, status.HTTP_401_UNAUTHORIZED, response.json()
        )

    def test_remove_groups_anonymous(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        to_delete = PeopleGroupFactory()
        project.member_people_groups.add(PeopleGroupFactory(), to_delete)

        payload = {Project.DefaultGroup.PEOPLE_GROUPS: [to_delete.id]}
        response = self.client.post(
            reverse("Project-remove-member", args=[project.id]), data=payload
        )
        self.assertEqual(
            response.status_code, status.HTTP_401_UNAUTHORIZED, response.json()
        )

    def test_add_linked_projects_anonymous(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        owner = UserFactory()
        project.members.add(owner)
        linked_projects = ProjectFactory.create_batch(
            3, publication_status=Project.PublicationStatus.PUBLIC
        )
        for p in linked_projects:
            p.members.add(owner)
            LinkedProject.objects.create(project=p, target=project)

        payload = {
            "projects": [
                {
                    "project_id": p.id,
                    "target_id": project.id,
                }
                for p in linked_projects
            ]
        }
        response = self.client.post(
            reverse("LinkedProjects-add-many", args=[project.id]), data=payload
        )
        self.assertEqual(
            response.status_code, status.HTTP_401_UNAUTHORIZED, response.json()
        )

    def test_update_linked_projects_anonymous(self):
        project = ProjectFactory()
        linked_project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC
        )
        owner = UserFactory()
        project.members.add(owner)
        linked_project.members.add(owner)
        LinkedProject.objects.create(project=linked_project, target=project)
        link = LinkedProjectFactory(project=linked_project, target=project)

        response = self.client.patch(
            reverse("LinkedProjects-detail", args=[project.id, link.id])
        )
        self.assertEqual(
            response.status_code, status.HTTP_401_UNAUTHORIZED, response.json()
        )

    def test_remove_linked_projects_anonymous(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        linked_project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC
        )
        owner = UserFactory()
        project.members.add(owner)
        linked_project.members.add(owner)
        LinkedProject.objects.create(project=linked_project, target=project)

        payload = {"project_ids": [linked_project.id]}
        response = self.client.delete(
            reverse("LinkedProjects-delete-many", args=(project.id,)), data=payload
        )
        self.assertEqual(
            response.status_code, status.HTTP_401_UNAUTHORIZED, response.json()
        )

    def test_read_linked_projects_anonymous(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        linked_project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC
        )
        linked_project2 = ProjectFactory(
            publication_status=Project.PublicationStatus.PRIVATE
        )
        linked_project3 = ProjectFactory(
            publication_status=Project.PublicationStatus.ORG
        )
        LinkedProjectFactory(project=linked_project, target=project)
        LinkedProjectFactory(project=linked_project2, target=project)
        LinkedProjectFactory(project=linked_project3, target=project)
        response = self.client.get(reverse("Project-detail", args=(project.id,)))
        linked_projects = response.json()["linked_projects"]
        self.assertEqual(len(linked_projects), 1)
        self.assertEqual(linked_projects[0]["project"]["id"], linked_project.id)


class ProjectTestCaseUserNoSDGsNoTagsNoImages(ProjectJwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.test_image = cls.get_test_image()

    def setUp(self):
        self.org = OrganizationFactory()
        self.fake = ProjectFactory.build(header_image=self.test_image)
        self.pc = ProjectCategoryFactory(
            background_image=self.test_image, organization=self.org
        )

    def _test(self, payload):
        self.client.force_authenticate(UserFactory())
        response = self.client.post(reverse("Project-list"), data=payload)
        self.assertEqual(
            response.status_code, status.HTTP_201_CREATED, response.content
        )

        content = response.json()
        self.assertIn("id", content)

        project = Project.objects.get(id=content["id"])
        self.assertEqual(self.fake.title, project.title)
        self.assertEqual(self.fake.description, project.description)
        self.assertEqual(self.fake.header_image.id, project.header_image.id)
        self.assertEqual(self.fake.is_shareable, project.is_shareable)
        self.assertEqual(self.fake.purpose, project.purpose)
        self.assertEqual(self.fake.language, project.language)
        self.assertEqual(self.fake.publication_status, project.publication_status)
        self.assertEqual(self.fake.life_status, project.life_status)
        self.assertEqual([], project.sdgs)
        self.assertEqual(
            set(project.categories.all().values_list("id", flat=True)), {self.pc.id}
        )

    def test_create_user_sdgs_missing(self):
        self._test(
            {
                "title": self.fake.title,
                "description": self.fake.description,
                "header_image_id": self.fake.header_image.id,
                "is_shareable": self.fake.is_shareable,
                "purpose": self.fake.purpose,
                "language": self.fake.language,
                "publication_status": self.fake.publication_status,
                "life_status": self.fake.life_status,
                "project_categories_ids": [self.pc.id],
                "organizations_codes": [self.org.code],
            }
        )

    def test_create_user_sdgs_empty(self):
        self._test(
            {
                "title": self.fake.title,
                "description": self.fake.description,
                "header_image_id": self.fake.header_image.id,
                "is_shareable": self.fake.is_shareable,
                "purpose": self.fake.purpose,
                "language": self.fake.language,
                "publication_status": self.fake.publication_status,
                "life_status": self.fake.life_status,
                "project_categories_ids": [self.pc.id],
                "organizations_codes": [self.org.code],
                "sdgs": [],
            }
        )


class ProjectTestCaseNoPermission(ProjectJwtAPITestCase, TagTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.test_image = cls.get_test_image()

    @patch(target="apps.misc.api.get_tag_from_wikipedia_gw")
    def test_create_no_permission(self, mocked):
        mocked.side_effect = self.side_effect
        org = OrganizationFactory()
        fake = ProjectFactory.build(header_image=self.test_image)
        pc = ProjectCategoryFactory(background_image=self.test_image, organization=org)
        wikipedia_tags = ["Q1735684"]
        images = [i.id for i in [self.get_test_image() for _ in range(2)]]
        organization_tags = TagFactory.create_batch(3, organization=org)
        payload = {
            "title": fake.title,
            "description": fake.description,
            "header_image_id": fake.header_image.id,
            "is_shareable": fake.is_shareable,
            "purpose": fake.purpose,
            "language": fake.language,
            "publication_status": fake.publication_status,
            "life_status": fake.life_status,
            "sdgs": fake.sdgs,
            "project_categories_ids": [pc.id],
            "wikipedia_tags_ids": wikipedia_tags,
            "organization_tags_ids": [t.id for t in organization_tags],
            "images_ids": images,
            "organizations_codes": [org.code],
        }
        self.client.force_authenticate(UserFactory())
        response = self.client.post(reverse("Project-list"), data=payload)
        self.assertEqual(
            response.status_code, status.HTTP_201_CREATED, response.content
        )

        content = response.json()
        self.assertIn("id", content)

        project = Project.objects.get(id=content["id"])
        self.assertEqual(fake.title, project.title)
        self.assertEqual(fake.description, project.description)
        self.assertEqual(fake.is_shareable, project.is_shareable)
        self.assertEqual(fake.purpose, project.purpose)
        self.assertEqual(fake.language, project.language)
        self.assertEqual(fake.publication_status, project.publication_status)
        self.assertEqual(fake.life_status, project.life_status)
        self.assertEqual(fake.sdgs, project.sdgs)
        self.assertEqual(
            set(project.categories.all().values_list("id", flat=True)), {pc.id}
        )
        self.assertEqual(
            [org.id],
            list(project.organizations.all().values_list("id", flat=True)),
        )
        self.assertEqual(
            set(wikipedia_tags),
            set(project.wikipedia_tags.all().values_list("wikipedia_qid", flat=True)),
        )
        self.assertEqual(
            {t.id for t in organization_tags},
            set(project.organization_tags.all().values_list("id", flat=True)),
        )
        payload["description"] = self.get_base64_image()
        response = self.client.post(reverse("Project-list"), data=payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.json())
        self.assertEqual(len(response.json()["images"]), 3)

    def test_destroy_no_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        self.client.force_authenticate(UserFactory())
        response = self.client.delete(reverse("Project-detail", args=(project.id,)))
        self.assertEqual(
            response.status_code, status.HTTP_403_FORBIDDEN, response.content
        )

    @patch(target="apps.misc.api.get_tag_from_wikipedia_gw")
    def test_update_no_permission(self, mocked):
        mocked.side_effect = self.side_effect
        pc = ProjectCategoryFactory(background_image=self.test_image)
        project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC, categories=[pc]
        )
        organization_tags = TagFactory.create_batch(
            3, organization=project.organizations.first()
        )
        payload = {
            "title": project.title,
            "description": project.description,
            "is_shareable": project.is_shareable,
            "purpose": project.purpose,
            "language": project.language,
            "publication_status": project.publication_status,
            "life_status": project.life_status,
            "sdgs": project.sdgs,
            "project_categories_ids": [pc.id],
            "organizations_codes": list(
                project.organizations.values_list("code", flat=True)
            ),
            "wikipedia_tags_ids": ["Q1735684"],
            "organization_tags_ids": [t.id for t in organization_tags],
        }
        self.client.force_authenticate(UserFactory())
        response = self.client.put(
            reverse("Project-detail", args=(project.id,)), data=payload
        )
        self.assertEqual(
            response.status_code, status.HTTP_403_FORBIDDEN, response.json()
        )

    def test_partial_update_no_permission(self):
        pc = ProjectCategoryFactory(background_image=self.test_image)
        project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC, categories=[pc]
        )
        payload = {"title": "NewTitle"}
        self.client.force_authenticate(UserFactory())
        response = self.client.patch(
            reverse("Project-detail", args=(project.id,)), data=payload
        )
        self.assertEqual(
            response.status_code, status.HTTP_403_FORBIDDEN, response.content
        )

    def test_duplicate_no_permission(self):
        pc = ProjectCategoryFactory(background_image=self.test_image)
        project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            categories=[pc],
        )
        self.client.force_authenticate(UserFactory())
        response = self.client.post(reverse("Project-duplicate", args=(project.id,)))
        self.assertEqual(
            response.status_code, status.HTTP_403_FORBIDDEN, response.json()
        )

    def test_add_members_no_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        project.members.add(UserFactory())

        member = UserFactory()
        payload = {
            Project.DefaultGroup.MEMBERS: [member.keycloak_id],
        }
        self.client.force_authenticate(UserFactory())
        response = self.client.post(
            reverse("Project-add-member", args=(project.id,)), data=payload
        )
        self.assertEqual(
            response.status_code, status.HTTP_403_FORBIDDEN, response.json()
        )

    def test_update_members_no_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        member = UserFactory()
        project.members.add(UserFactory(), member)

        payload = {Project.DefaultGroup.OWNERS: [member.keycloak_id]}
        self.client.force_authenticate(UserFactory())
        response = self.client.post(
            reverse("Project-add-member", args=[project.id]), data=payload
        )
        self.assertEqual(
            response.status_code, status.HTTP_403_FORBIDDEN, response.content
        )

    def test_remove_members_no_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        to_delete = UserFactory()
        project.members.add(UserFactory(), to_delete)

        payload = {"users": [to_delete.keycloak_id]}
        self.client.force_authenticate(UserFactory())
        response = self.client.post(
            reverse("Project-remove-member", args=(project.id,)), data=payload
        )
        self.assertEqual(
            response.status_code, status.HTTP_403_FORBIDDEN, response.json()
        )

    def test_add_linked_projects_no_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        owner = UserFactory()
        project.members.add(owner)
        linked_projects = ProjectFactory.create_batch(
            3, publication_status=Project.PublicationStatus.PUBLIC
        )
        for p in linked_projects:
            p.members.add(owner)
            LinkedProject.objects.create(project=p, target=project)

        payload = {
            "projects": [
                {
                    "project_id": p.id,
                    "target_id": project.id,
                }
                for p in linked_projects
            ]
        }
        self.client.force_authenticate(UserFactory())
        response = self.client.post(
            reverse("LinkedProjects-add-many", args=(project.id,)), data=payload
        )
        self.assertEqual(
            response.status_code, status.HTTP_403_FORBIDDEN, response.content
        )

    def test_update_linked_projects_no_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        linked_project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC
        )
        owner = UserFactory()
        project.members.add(owner)
        linked_project.members.add(owner)
        LinkedProject.objects.create(project=linked_project, target=project)
        link = LinkedProjectFactory(project=linked_project, target=project)

        self.client.force_authenticate(UserFactory())
        response = self.client.patch(
            reverse("LinkedProjects-detail", args=[project.id, link.id])
        )
        self.assertEqual(
            response.status_code, status.HTTP_403_FORBIDDEN, response.content
        )

    def test_remove_linked_projects_no_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        linked_project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC
        )
        owner = UserFactory()
        project.members.add(owner)
        linked_project.members.add(owner)
        LinkedProject.objects.create(project=linked_project, target=project)

        payload = {"project_ids": [linked_project.id]}
        self.client.force_authenticate(UserFactory())
        response = self.client.delete(
            reverse("LinkedProjects-delete-many", args=(project.id,)), data=payload
        )
        self.assertEqual(
            response.status_code, status.HTTP_403_FORBIDDEN, response.json()
        )

    def test_read_linked_projects_no_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        linked_project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC
        )
        linked_project2 = ProjectFactory(
            publication_status=Project.PublicationStatus.PRIVATE
        )
        linked_project3 = ProjectFactory(
            publication_status=Project.PublicationStatus.ORG
        )
        LinkedProject.objects.create(project=linked_project, target=project)
        LinkedProject.objects.create(project=linked_project2, target=project)
        LinkedProject.objects.create(project=linked_project3, target=project)

        self.client.force_authenticate(UserFactory())
        response = self.client.get(reverse("Project-detail", args=(project.id,)))
        linked_projects = response.json()["linked_projects"]
        self.assertEqual(len(linked_projects), 1)
        self.assertEqual(linked_projects[0]["project"]["id"], linked_project.id)


class ProjectTestCaseBasePermission(ProjectJwtAPITestCase, TagTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.test_image = cls.get_test_image()

    def test_destroy_base_permission(self):
        public = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        private = ProjectFactory(publication_status=Project.PublicationStatus.PRIVATE)
        in_org = ProjectFactory(publication_status=Project.PublicationStatus.ORG)
        in_org_private = ProjectFactory(
            publication_status=Project.PublicationStatus.PRIVATE
        )
        organization = OrganizationFactory()
        in_org.organizations.add(organization)
        user = UserFactory(
            permissions=[
                ("projects.view_project", None),
                ("projects.delete_project", None),
            ]
        )
        self.client.force_authenticate(user)

        response = self.client.delete(reverse("Project-detail", args=(public.id,)))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        response = self.client.delete(reverse("Project-detail", args=(private.id,)))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        response = self.client.delete(reverse("Project-detail", args=(in_org.id,)))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        response = self.client.delete(
            reverse("Project-detail", args=(in_org_private.id,))
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    @patch(target="apps.misc.api.get_tag_from_wikipedia_gw")
    def test_update_base_permission(self, mocked):
        mocked.side_effect = self.side_effect
        organization = OrganizationFactory()
        pc = ProjectCategoryFactory(
            background_image=self.test_image, organization=organization
        )
        project = ProjectFactory(
            publication_status=Project.PublicationStatus.PRIVATE, categories=[pc]
        )
        organization_tags = TagFactory.create_batch(3, organization=organization)
        project.organizations.add(organization)
        payload = {
            "title": "NewTitle",
            "description": project.description,
            "is_shareable": project.is_shareable,
            "purpose": project.purpose,
            "language": project.language,
            "publication_status": project.publication_status,
            "life_status": project.life_status,
            "sdgs": project.sdgs,
            "project_categories_ids": [pc.id],
            "organizations_codes": list(
                project.organizations.values_list("code", flat=True)
            ),
            "wikipedia_tags_ids": ["Q1735684"],
            "organization_tags_ids": [t.id for t in organization_tags],
        }
        user = UserFactory(
            permissions=[
                ("projects.view_project", None),
                ("projects.change_project", None),
            ]
        )
        self.client.force_authenticate(user)
        response = self.client.put(
            reverse("Project-detail", args=(project.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        project.refresh_from_db()
        self.assertEqual(project.title, "NewTitle")

    def test_partial_update_base_permission(self):
        pc = ProjectCategoryFactory(background_image=self.test_image)
        organization = OrganizationFactory()
        pc = ProjectCategoryFactory(
            background_image=self.test_image, organization=organization
        )
        project = ProjectFactory(
            publication_status=Project.PublicationStatus.PRIVATE,
            categories=[pc],
            organizations=[organization],
        )
        new_organizations = OrganizationFactory.create_batch(5)
        payload = {
            "title": "NewTitle",
            "organizations_codes": [o.code for o in new_organizations],
            "project_category_id": ProjectCategoryFactory(
                organization=new_organizations[0]
            ).id,
        }
        user = UserFactory(
            permissions=[
                ("projects.view_project", None),
                ("projects.change_project", None),
            ]
        )
        self.client.force_authenticate(user)
        response = self.client.patch(
            reverse("Project-detail", args=(project.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        project.refresh_from_db()
        self.assertEqual(project.title, "NewTitle")
        self.assertEqual(project.organizations.count(), 5)

    def test_duplicate_base_permission(self):
        pc = ProjectCategoryFactory()
        project = ProjectFactory(
            publication_status=Project.PublicationStatus.PRIVATE,
            categories=[pc],
            header_image=self.get_test_image(),
        )
        blog_entries = BlogEntryFactory.create_batch(3, project=project)
        GoalFactory.create_batch(3, project=project)
        AttachmentLinkFactory.create_batch(3, project=project)
        AttachmentFileFactory.create_batch(3, project=project)
        AnnouncementFactory.create_batch(3, project=project)
        images = [self.get_test_image() for _ in range(3)]
        project.images.set(images)
        project.description = "\n".join(
            [f'<img src="/v1/project/{project.pk}/image/{i.pk}/" />' for i in images]
        )
        project.save()
        blog_entries_images = [self.get_test_image() for _ in range(3)]
        blog_entries[0].images.add(*blog_entries_images)
        blog_entries[0].content = "\n".join(
            [
                f'<img src="/v1/project/{project.pk}/blog-entry-image/{i.pk}/" />'
                for i in blog_entries_images
            ]
        )
        blog_entries[0].save()
        user = UserFactory(
            permissions=[
                ("projects.view_project", None),
                ("projects.duplicate_project", None),
            ]
        )
        self.client.force_authenticate(user)
        duplicated_project_response = self.client.post(
            reverse("Project-duplicate", args=(project.id,))
        )
        initial_project_response = self.client.get(
            reverse("Project-detail", args=(project.id,))
        )
        assert duplicated_project_response.status_code == status.HTTP_201_CREATED
        assert initial_project_response.status_code == status.HTTP_200_OK
        duplicated_project = duplicated_project_response.json()
        initial_project = initial_project_response.json()

        fields = [
            "is_locked",
            "title",
            "is_shareable",
            "purpose",
            "language",
            "publication_status",
            "life_status",
            "template",
        ]
        many_to_many_fields = [
            "categories",
            "wikipedia_tags",
            "organization_tags",
            "linked_projects",
        ]
        related_fields = [
            "goals",
            "links",
            "files",
            "announcements",
            "locations",
        ]
        list_fields = ["sdgs"]

        for field in fields:
            assert duplicated_project[field] == initial_project[field]

        for field in list_fields:
            assert set(duplicated_project[field]) == set(initial_project[field])

        for field in many_to_many_fields:
            assert set([item["id"] for item in duplicated_project[field]]) == set(
                [item["id"] for item in initial_project[field]]
            )

        for related_field in related_fields:
            assert len(duplicated_project[related_field]) == len(
                initial_project[related_field]
            )
            duplicated_field = [
                {
                    key: value
                    for key, value in item.items()
                    if key not in ["id", "project", "updated_at"]
                }
                for item in duplicated_project[related_field]
            ]
            initial_field = [
                {
                    key: value
                    for key, value in item.items()
                    if key not in ["id", "project", "updated_at"]
                }
                for item in initial_project[related_field]
            ]
            assert len(duplicated_field) == len(initial_field)
            assert all(item in initial_field for item in duplicated_field)

        assert len(duplicated_project["images"]) == len(initial_project["images"])
        assert all(
            di["id"] not in [ii["id"] for ii in initial_project["images"]]
            for di in duplicated_project["images"]
        )
        assert all(
            f"<img src=\"/v1/project/{duplicated_project['id']}/image/{i['id']}/\" />"
            in duplicated_project["description"]
            for i in duplicated_project["images"]
        )

        assert len(duplicated_project["blog_entries"]) == len(
            initial_project["blog_entries"]
        )
        assert all(
            dbe["id"] not in [ibe["id"] for ibe in initial_project["blog_entries"]]
            for dbe in duplicated_project["blog_entries"]
        )
        initial_blog_entry = list(
            filter(lambda x: len(x["images"]) > 0, initial_project["blog_entries"])
        )[0]
        duplicated_blog_entry = list(
            filter(lambda x: len(x["images"]) > 0, duplicated_project["blog_entries"])
        )[0]
        assert all(
            di not in initial_blog_entry["images"]
            for di in duplicated_blog_entry["images"]
        )
        assert all(
            f"<img src=\"/v1/project/{duplicated_project['id']}/blog-entry-image/{di}/\" />"
            in duplicated_blog_entry["content"]
            for di in duplicated_blog_entry["images"]
        )

    def test_add_members_base_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        member = UserFactory()
        payload = {
            Project.DefaultGroup.MEMBERS: [member.keycloak_id],
        }
        user = UserFactory(
            permissions=[
                ("projects.view_project", None),
                ("projects.change_project", None),
            ]
        )
        self.client.force_authenticate(user)
        response = self.client.post(
            reverse("Project-add-member", args=(project.id,)), data=payload
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert member in project.members.all()

    def test_remove_members_with_two_owner_base_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        to_delete = UserFactory()
        project.owners.add(to_delete)
        payload = {
            "users": [to_delete.keycloak_id],
        }
        user = UserFactory(
            permissions=[
                ("projects.view_project", None),
                ("projects.change_project", None),
            ]
        )
        self.client.force_authenticate(user)
        response = self.client.post(
            reverse("Project-remove-member", args=(project.id,)), data=payload
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert to_delete not in project.owners.all()

    def test_remove_members_self(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        to_delete = UserFactory()
        project.members.add(to_delete)
        self.client.force_authenticate(to_delete)
        response = self.client.delete(
            reverse("Project-remove-self", args=(project.id,))
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert to_delete not in project.members.all()

    def test_remove_members_with_one_owner_base_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        owner = UserFactory()
        project.get_owners().users.clear()
        project.owners.add(owner)
        payload = {
            "users": [owner.keycloak_id],
        }
        user = UserFactory(
            permissions=[
                ("projects.view_project", None),
                ("projects.change_project", None),
            ]
        )
        self.client.force_authenticate(user)
        response = self.client.post(
            reverse("Project-remove-member", args=(project.id,)), data=payload
        )
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.content
        )
        content = response.json()
        self.assertEqual(
            content["users"],
            {"users": "You cannot remove all the owners of a project."},
        )

    def test_add_linked_projects_base_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.ORG)
        owner = UserFactory()
        project.members.add(owner)
        linked_projects = ProjectFactory.create_batch(
            3, publication_status=Project.PublicationStatus.ORG
        )
        for p in linked_projects:
            p.members.add(owner)

        payload = {
            "projects": [
                {"project_id": p.id, "target_id": project.id} for p in linked_projects
            ]
        }
        user = UserFactory(
            permissions=[
                ("projects.change_project", None),
                ("projects.view_project", None),
            ]
        )
        self.client.force_authenticate(user)
        response = self.client.post(
            reverse("LinkedProjects-add-many", args=(project.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

        content = response.json()
        self.assertEqual(len(content["linked_projects"]), 3)

    def test_update_linked_projects_base_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        linked_project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC
        )
        owner = UserFactory()
        project.members.add(owner)
        linked_project.members.add(owner)
        link = LinkedProject.objects.create(project=linked_project, target=project)

        user = UserFactory(
            permissions=[
                ("projects.change_project", None),
                ("projects.view_project", None),
            ]
        )
        self.client.force_authenticate(user)
        response = self.client.patch(
            reverse("LinkedProjects-detail", args=[project.id, link.id])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

    def test_remove_linked_projects_base_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        linked_project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC
        )
        to_unlinked_project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC
        )
        owner = UserFactory()
        project.members.add(owner)
        linked_project.members.add(owner)
        to_unlinked_project.members.add(owner)
        LinkedProject.objects.create(project=linked_project, target=project)
        LinkedProject.objects.create(project=to_unlinked_project, target=project)

        payload = {"project_ids": [to_unlinked_project.id]}
        user = UserFactory(
            permissions=[
                ("projects.change_project", None),
                ("projects.view_project", None),
            ]
        )
        self.client.force_authenticate(user)
        response = self.client.delete(
            reverse("LinkedProjects-delete-many", args=(project.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

    def test_read_linked_projects_base_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        linked_project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC
        )
        linked_project2 = ProjectFactory(
            publication_status=Project.PublicationStatus.PRIVATE
        )
        linked_project3 = ProjectFactory(
            publication_status=Project.PublicationStatus.ORG
        )
        LinkedProjectFactory(project=linked_project, target=project)
        LinkedProjectFactory(project=linked_project2, target=project)
        LinkedProjectFactory(project=linked_project3, target=project)

        user = UserFactory()
        self.client.force_authenticate(user)
        response = self.client.get(reverse("Project-detail", args=(project.id,)))
        linked_projects = response.json()["linked_projects"]
        self.assertEqual(len(linked_projects), 1)
        self.assertEqual(
            linked_projects[0]["project"]["id"],
            linked_project.id,
        )


class ProjectLockUnlockTestCase(ProjectJwtAPITestCase, TagTestCase):
    def test_lock_unlock_without_permission(self):
        user = UserFactory(
            permissions=[
                ("projects.view_project", None),
            ]
        )
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        self.client.force_authenticate(user)

        response = self.client.post(reverse("Project-unlock", args=[project.id]))
        assert response.status_code == 403

        response = self.client.post(reverse("Project-lock", args=[project.id]))
        assert response.status_code == 403

    def test_lock_unlock(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        user = UserFactory(
            permissions=[
                ("projects.lock_project", None),
                ("projects.view_project", None),
            ]
        )
        self.client.force_authenticate(user)

        response = self.client.post(reverse("Project-unlock", args=[project.id]))
        assert response.status_code == 200

        response = self.client.post(reverse("Project-lock", args=[project.id]))
        assert response.status_code == 200


class ProjectTestCaseProjectPermission(ProjectJwtAPITestCase, TagTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.test_image = cls.get_test_image()

    def test_destroy_project_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.ORG)
        organization = OrganizationFactory()
        project.organizations.add(organization)
        user = UserFactory(
            permissions=[
                ("projects.delete_project", project),
                ("projects.view_project", project),
            ]
        )
        self.client.force_authenticate(user)
        response = self.client.delete(reverse("Project-detail", args=(project.id,)))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    @patch(target="apps.misc.api.get_tag_from_wikipedia_gw")
    def test_update_project_permission(self, mocked):
        mocked.side_effect = self.side_effect
        organization = OrganizationFactory()
        pc = ProjectCategoryFactory(
            background_image=self.test_image, organization=organization
        )
        project = ProjectFactory(
            publication_status=Project.PublicationStatus.PRIVATE, categories=[pc]
        )
        organization_tags = TagFactory.create_batch(3, organization=organization)
        project.organizations.add(organization)
        payload = {
            "title": "NewTitle",
            "description": project.description,
            "is_shareable": project.is_shareable,
            "purpose": project.purpose,
            "language": project.language,
            "publication_status": project.publication_status,
            "life_status": project.life_status,
            "sdgs": project.sdgs,
            "project_categories_ids": [pc.id],
            "organizations_codes": list(
                project.organizations.values_list("code", flat=True)
            ),
            "wikipedia_tags_ids": ["Q1735684"],
            "organization_tags_ids": [t.id for t in organization_tags],
        }
        user = UserFactory(
            permissions=[
                ("projects.change_project", project),
                ("projects.view_project", project),
            ]
        )
        self.client.force_authenticate(user)
        response = self.client.put(
            reverse("Project-detail", args=(project.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        project.refresh_from_db()
        self.assertEqual(project.title, "NewTitle")
        payload["description"] = self.get_base64_image()
        response = self.client.put(
            reverse("Project-detail", args=(project.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        self.assertEqual(len(response.json()["images"]), 1)

    def test_partial_update_project_permission(self):
        organization = OrganizationFactory()
        pc = ProjectCategoryFactory(
            background_image=self.test_image, organization=organization
        )
        project = ProjectFactory(
            publication_status=Project.PublicationStatus.PRIVATE,
            categories=[pc],
            organizations=[organization],
        )
        payload = {"title": "NewTitle"}
        user = UserFactory(
            permissions=[
                ("projects.change_project", project),
                ("projects.view_project", project),
            ]
        )
        self.client.force_authenticate(user)
        response = self.client.patch(
            reverse("Project-detail", args=(project.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        project.refresh_from_db()
        self.assertEqual(project.title, "NewTitle")
        payload["description"] = self.get_base64_image()
        response = self.client.patch(
            reverse("Project-detail", args=(project.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        self.assertEqual(len(response.json()["images"]), 1)

    def test_update_without_organization(self):
        project = ProjectFactory()
        user = UserFactory(
            permissions=[
                ("projects.change_project", project),
                ("projects.view_project", project),
            ]
        )
        self.client.force_authenticate(user)
        payload = {"organizations_codes": [], "title": "new-title"}
        self.client.force_authenticate(user)
        response = self.client.put(
            reverse("Project-detail", args=(project.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("organizations_codes", response.data)

    def test_duplicate_project_permission(self):
        pc = ProjectCategoryFactory()
        project = ProjectFactory(
            publication_status=Project.PublicationStatus.PRIVATE,
            categories=[pc],
            header_image=self.get_test_image(),
        )
        user = UserFactory(
            permissions=[
                ("projects.duplicate_project", project),
                ("projects.view_project", project),
            ]
        )
        blog_entries = BlogEntryFactory.create_batch(3, project=project)
        GoalFactory.create_batch(3, project=project)
        AttachmentLinkFactory.create_batch(3, project=project)
        AttachmentFileFactory.create_batch(3, project=project)
        AnnouncementFactory.create_batch(3, project=project)
        images = [self.get_test_image() for _ in range(3)]
        project.images.set(images)
        project.description = "\n".join(
            [f'<img src="/v1/project/{project.pk}/image/{i.pk}/" />' for i in images]
        )
        project.save()
        blog_entries_images = [self.get_test_image() for _ in range(3)]
        blog_entries[0].images.add(*blog_entries_images)
        blog_entries[0].content = "\n".join(
            [
                f'<img src="/v1/project/{project.pk}/blog-entry-image/{i.pk}/" />'
                for i in blog_entries_images
            ]
        )
        blog_entries[0].save()
        self.client.force_authenticate(user)
        duplicated_project_response = self.client.post(
            reverse("Project-duplicate", args=(project.id,))
        )
        initial_project_response = self.client.get(
            reverse("Project-detail", args=(project.id,))
        )
        assert duplicated_project_response.status_code == status.HTTP_201_CREATED
        assert initial_project_response.status_code == status.HTTP_200_OK
        duplicated_project = duplicated_project_response.json()
        initial_project = initial_project_response.json()

        fields = [
            "is_locked",
            "title",
            "is_shareable",
            "purpose",
            "language",
            "publication_status",
            "life_status",
            "template",
        ]
        many_to_many_fields = [
            "categories",
            "wikipedia_tags",
            "organization_tags",
            "linked_projects",
        ]
        related_fields = [
            "goals",
            "links",
            "files",
            "announcements",
            "locations",
        ]
        list_fields = ["sdgs"]

        for field in fields:
            assert duplicated_project[field] == initial_project[field]

        for field in list_fields:
            assert set(duplicated_project[field]) == set(initial_project[field])

        for field in many_to_many_fields:
            assert set([item["id"] for item in duplicated_project[field]]) == set(
                [item["id"] for item in initial_project[field]]
            )

        for related_field in related_fields:
            assert len(duplicated_project[related_field]) == len(
                initial_project[related_field]
            )
            duplicated_field = [
                {
                    key: value
                    for key, value in item.items()
                    if key not in ["id", "project", "updated_at"]
                }
                for item in duplicated_project[related_field]
            ]
            initial_field = [
                {
                    key: value
                    for key, value in item.items()
                    if key not in ["id", "project", "updated_at"]
                }
                for item in initial_project[related_field]
            ]
            assert len(duplicated_field) == len(initial_field)
            assert all(item in initial_field for item in duplicated_field)

        assert len(duplicated_project["images"]) == len(initial_project["images"])
        assert all(
            di["id"] not in [ii["id"] for ii in initial_project["images"]]
            for di in duplicated_project["images"]
        )
        assert all(
            f"<img src=\"/v1/project/{duplicated_project['id']}/image/{i['id']}/\" />"
            in duplicated_project["description"]
            for i in duplicated_project["images"]
        )

        assert len(duplicated_project["blog_entries"]) == len(
            initial_project["blog_entries"]
        )
        assert all(
            dbe["id"] not in [ibe["id"] for ibe in initial_project["blog_entries"]]
            for dbe in duplicated_project["blog_entries"]
        )
        initial_blog_entry = list(
            filter(lambda x: len(x["images"]) > 0, initial_project["blog_entries"])
        )[0]
        duplicated_blog_entry = list(
            filter(lambda x: len(x["images"]) > 0, duplicated_project["blog_entries"])
        )[0]
        assert all(
            di not in initial_blog_entry["images"]
            for di in duplicated_blog_entry["images"]
        )
        assert all(
            f"<img src=\"/v1/project/{duplicated_project['id']}/blog-entry-image/{di}/\" />"
            in duplicated_blog_entry["content"]
            for di in duplicated_blog_entry["images"]
        )

    def test_add_members_project_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        member = UserFactory()
        payload = {
            Project.DefaultGroup.MEMBERS: [member.keycloak_id],
        }
        user = UserFactory(
            permissions=[
                ("projects.change_project", project),
                ("projects.view_project", project),
            ]
        )
        self.client.force_authenticate(user)
        response = self.client.post(
            reverse("Project-add-member", args=(project.id,)), data=payload
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert project.get_all_members().count() == 2

    def test_remove_members_with_two_owners_project_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        user_to_delete = UserFactory()
        project.owners.add(user_to_delete)
        payload = {
            "users": [user_to_delete.keycloak_id],
        }
        self.client.force_authenticate(project.owners.first())
        response = self.client.post(
            reverse("Project-remove-member", args=[project.id]), data=payload
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert project.owners.count() == 1

    def test_remove_members_with_one_owner_project_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        owner = UserFactory()
        project.get_owners().users.clear()
        project.owners.add(owner)
        payload = {
            "users": [owner.keycloak_id],
        }
        user = UserFactory(
            permissions=[
                ("projects.change_project", project),
                ("projects.view_project", project),
            ]
        )
        self.client.force_authenticate(user)
        response = self.client.post(
            reverse("Project-remove-member", args=(project.id,)), data=payload
        )
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.content
        )
        content = response.json()
        self.assertEqual(
            content["users"],
            {"users": "You cannot remove all the owners of a project."},
        )

    def test_add_linked_projects_project_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.ORG)
        owner = UserFactory()
        project.members.add(owner)
        linked_projects = ProjectFactory.create_batch(
            3, publication_status=Project.PublicationStatus.ORG
        )
        for p in linked_projects:
            p.members.add(owner)

        payload = {
            "projects": [
                {"project_id": p.id, "target_id": project.id} for p in linked_projects
            ]
        }
        organization = OrganizationFactory()
        user = UserFactory(
            permissions=[
                ("projects.change_project", project),
                ("organizations.view_project", organization),
            ]
        )
        organization.projects.add(
            project, linked_projects[0], linked_projects[1], linked_projects[2]
        )

        self.client.force_authenticate(user)
        response = self.client.post(
            reverse("LinkedProjects-add-many", args=(project.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

        content = response.json()
        self.assertEqual(len(content["linked_projects"]), 3)
        self.assertEqual(
            {p["project"]["id"] for p in content["linked_projects"]},
            {p.id for p in linked_projects},
        )

    def test_update_linked_projects_project_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        linked_project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC
        )
        owner = UserFactory()
        project.members.add(owner)
        linked_project.members.add(owner)
        link = LinkedProject.objects.create(project=linked_project, target=project)

        user = UserFactory(
            permissions=[
                ("projects.change_project", project),
                ("projects.view_project", project),
            ]
        )
        self.client.force_authenticate(user)
        response = self.client.patch(
            reverse("LinkedProjects-detail", args=[project.id, link.id])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

    def test_remove_linked_projects_project_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        linked_project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC
        )
        to_unlinked_project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC
        )
        owner = UserFactory()
        project.members.add(owner)
        linked_project.members.add(owner)
        to_unlinked_project.members.add(owner)
        LinkedProject.objects.create(project=linked_project, target=project)
        LinkedProject.objects.create(project=to_unlinked_project, target=project)

        payload = {"project_ids": [to_unlinked_project.id]}
        user = UserFactory(
            permissions=[
                ("projects.change_project", project),
                ("projects.view_project", project),
            ]
        )
        self.client.force_authenticate(user)
        response = self.client.delete(
            reverse("LinkedProjects-delete-many", args=(project.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

        content = response.json()
        self.assertEqual(len(content["linked_projects"]), 1)
        self.assertEqual(
            content["linked_projects"][0]["project"]["id"], linked_project.id
        )

    def test_read_linked_projects_project_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        linked_project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC
        )
        linked_project2 = ProjectFactory(
            publication_status=Project.PublicationStatus.PRIVATE
        )
        linked_project3 = ProjectFactory(
            publication_status=Project.PublicationStatus.ORG
        )
        LinkedProject.objects.create(project=linked_project, target=project)
        LinkedProject.objects.create(project=linked_project2, target=project)
        LinkedProject.objects.create(project=linked_project3, target=project)

        user = UserFactory(
            permissions=[
                ("projects.view_project", linked_project2),
            ]
        )
        self.client.force_authenticate(user)
        response = self.client.get(reverse("Project-detail", args=(project.id,)))
        linked_projects = response.json()["linked_projects"]
        self.assertEqual(len(linked_projects), 2)
        self.assertEqual(
            sorted(
                [
                    linked_projects[0]["project"]["id"],
                    linked_projects[1]["project"]["id"],
                ]
            ),
            sorted([linked_project.id, linked_project2.id]),
        )

    def test_update_locked(self):
        project = ProjectFactory(is_locked=True)
        user = UserFactory(
            permissions=[
                ("projects.change_project", project),
                ("projects.view_project", project),
            ]
        )
        self.client.force_authenticate(user)
        response = self.client.patch(reverse("Project-detail", args=[project.id]), {})
        assert response.status_code == 403


class ProjectTestCaseOrgPermission(ProjectJwtAPITestCase, TagTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.test_image = cls.get_test_image()

    def test_destroy_org_permission(self):
        public = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        private = ProjectFactory(publication_status=Project.PublicationStatus.PRIVATE)
        in_org = ProjectFactory(publication_status=Project.PublicationStatus.ORG)
        in_org_private = ProjectFactory(
            publication_status=Project.PublicationStatus.PRIVATE
        )
        organization = OrganizationFactory()
        in_org.organizations.add(organization)
        in_org_private.organizations.add(organization)
        user = UserFactory(
            permissions=[
                ("organizations.delete_project", organization),
                ("organizations.view_project", organization),
            ]
        )
        self.client.force_authenticate(user)

        response = self.client.delete(reverse("Project-detail", args=(public.id,)))
        self.assertEqual(
            response.status_code, status.HTTP_403_FORBIDDEN, response.content
        )

        response = self.client.delete(reverse("Project-detail", args=(private.id,)))
        self.assertEqual(
            response.status_code, status.HTTP_403_FORBIDDEN, response.content
        )

        response = self.client.delete(reverse("Project-detail", args=(in_org.id,)))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        response = self.client.delete(
            reverse("Project-detail", args=(in_org_private.id,))
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    @patch(target="apps.misc.api.get_tag_from_wikipedia_gw")
    def test_update_org_permission(self, mocked):
        mocked.side_effect = self.side_effect
        organization = OrganizationFactory()
        pc = ProjectCategoryFactory(
            background_image=self.test_image, organization=organization
        )
        project = ProjectFactory(
            publication_status=Project.PublicationStatus.PRIVATE, categories=[pc]
        )
        project.organizations.add(organization)
        organization_tags = TagFactory.create_batch(3, organization=organization)
        payload = {
            "title": "NewTitle",
            "description": project.description,
            "is_shareable": project.is_shareable,
            "purpose": project.purpose,
            "language": project.language,
            "publication_status": project.publication_status,
            "life_status": project.life_status,
            "sdgs": project.sdgs,
            "project_categories_ids": [pc.id],
            "organizations_codes": list(
                project.organizations.values_list("code", flat=True)
            ),
            "wikipedia_tags_ids": ["Q1735684"],
            "organization_tags_ids": [t.id for t in organization_tags],
        }
        user = UserFactory(
            permissions=[
                ("organizations.change_project", organization),
                ("organizations.view_project", organization),
            ]
        )
        self.client.force_authenticate(user)
        response = self.client.put(
            reverse("Project-detail", args=(project.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        project.refresh_from_db()
        self.assertEqual(project.title, "NewTitle")
        payload["description"] = self.get_base64_image()
        response = self.client.put(
            reverse("Project-detail", args=(project.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        self.assertEqual(len(response.json()["images"]), 1)

    def test_partial_update_org_permission(self):
        pc = ProjectCategoryFactory(background_image=self.test_image)
        project = ProjectFactory(
            publication_status=Project.PublicationStatus.PRIVATE, categories=[pc]
        )
        organization = OrganizationFactory()
        project.organizations.add(organization)
        payload = {"title": "NewTitle"}
        user = UserFactory(
            permissions=[
                ("organizations.change_project", organization),
                ("organizations.view_project", organization),
            ]
        )
        self.client.force_authenticate(user)
        response = self.client.patch(
            reverse("Project-detail", args=(project.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        project.refresh_from_db()
        self.assertEqual(project.title, "NewTitle")
        payload["description"] = self.get_base64_image()
        response = self.client.patch(
            reverse("Project-detail", args=(project.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        self.assertEqual(len(response.json()["images"]), 1)

    def test_duplicate_org_permission(self):
        pc = ProjectCategoryFactory()
        project = ProjectFactory(
            publication_status=Project.PublicationStatus.PRIVATE,
            categories=[pc],
            header_image=self.get_test_image(),
        )
        organization = OrganizationFactory()
        project.organizations.add(organization)
        user = UserFactory(
            permissions=[
                ("organizations.duplicate_project", organization),
                ("organizations.view_project", organization),
            ]
        )
        blog_entries = BlogEntryFactory.create_batch(3, project=project)
        GoalFactory.create_batch(3, project=project)
        AttachmentLinkFactory.create_batch(3, project=project)
        AttachmentFileFactory.create_batch(3, project=project)
        AnnouncementFactory.create_batch(3, project=project)
        images = [self.get_test_image() for _ in range(3)]
        project.images.set(images)
        project.description = "\n".join(
            [f'<img src="/v1/project/{project.pk}/image/{i.pk}/" />' for i in images]
        )
        project.save()
        blog_entries_images = [self.get_test_image() for _ in range(3)]
        blog_entries[0].images.add(*blog_entries_images)
        blog_entries[0].content = "\n".join(
            [
                f'<img src="/v1/project/{project.pk}/blog-entry-image/{i.pk}/" />'
                for i in blog_entries_images
            ]
        )
        blog_entries[0].save()
        self.client.force_authenticate(user)
        duplicated_project_response = self.client.post(
            reverse("Project-duplicate", args=(project.id,))
        )
        initial_project_response = self.client.get(
            reverse("Project-detail", args=(project.id,))
        )
        assert duplicated_project_response.status_code == status.HTTP_201_CREATED
        assert initial_project_response.status_code == status.HTTP_200_OK
        duplicated_project = duplicated_project_response.json()
        initial_project = initial_project_response.json()

        fields = [
            "is_locked",
            "title",
            "is_shareable",
            "purpose",
            "language",
            "publication_status",
            "life_status",
            "template",
        ]
        many_to_many_fields = [
            "categories",
            "wikipedia_tags",
            "organization_tags",
            "linked_projects",
        ]
        related_fields = [
            "goals",
            "links",
            "files",
            "announcements",
            "locations",
        ]
        list_fields = ["sdgs"]

        for field in fields:
            assert duplicated_project[field] == initial_project[field]

        for field in list_fields:
            assert set(duplicated_project[field]) == set(initial_project[field])

        for field in many_to_many_fields:
            assert set([item["id"] for item in duplicated_project[field]]) == set(
                [item["id"] for item in initial_project[field]]
            )

        for related_field in related_fields:
            assert len(duplicated_project[related_field]) == len(
                initial_project[related_field]
            )
            duplicated_field = [
                {
                    key: value
                    for key, value in item.items()
                    if key not in ["id", "project", "updated_at"]
                }
                for item in duplicated_project[related_field]
            ]
            initial_field = [
                {
                    key: value
                    for key, value in item.items()
                    if key not in ["id", "project", "updated_at"]
                }
                for item in initial_project[related_field]
            ]
            assert len(duplicated_field) == len(initial_field)
            assert all(item in initial_field for item in duplicated_field)

        assert len(duplicated_project["images"]) == len(initial_project["images"])
        assert all(
            di["id"] not in [ii["id"] for ii in initial_project["images"]]
            for di in duplicated_project["images"]
        )
        assert all(
            f"<img src=\"/v1/project/{duplicated_project['id']}/image/{i['id']}/\" />"
            in duplicated_project["description"]
            for i in duplicated_project["images"]
        )

        assert len(duplicated_project["blog_entries"]) == len(
            initial_project["blog_entries"]
        )
        assert all(
            dbe["id"] not in [ibe["id"] for ibe in initial_project["blog_entries"]]
            for dbe in duplicated_project["blog_entries"]
        )
        initial_blog_entry = list(
            filter(lambda x: len(x["images"]) > 0, initial_project["blog_entries"])
        )[0]
        duplicated_blog_entry = list(
            filter(lambda x: len(x["images"]) > 0, duplicated_project["blog_entries"])
        )[0]
        assert all(
            di not in initial_blog_entry["images"]
            for di in duplicated_blog_entry["images"]
        )
        assert all(
            f"<img src=\"/v1/project/{duplicated_project['id']}/blog-entry-image/{di}/\" />"
            in duplicated_blog_entry["content"]
            for di in duplicated_blog_entry["images"]
        )

    def test_add_members_org_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        organization = OrganizationFactory()
        project.organizations.add(organization)
        member = UserFactory()
        payload = {
            Project.DefaultGroup.MEMBERS: [member.keycloak_id],
        }
        user = UserFactory(
            permissions=[
                ("organizations.change_project", organization),
                ("organizations.view_project", organization),
            ]
        )
        self.client.force_authenticate(user)
        response = self.client.post(
            reverse("Project-add-member", args=(project.id,)), data=payload
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert project.get_all_members().count() == 2

    def test_remove_members_with_two_owner_org_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        to_delete = UserFactory()
        project.owners.add(to_delete)
        organization = OrganizationFactory()
        project.organizations.add(organization)

        payload = {
            "users": [to_delete.keycloak_id],
        }
        user = UserFactory(
            permissions=[
                ("organizations.change_project", organization),
                ("organizations.view_project", organization),
            ]
        )
        self.client.force_authenticate(user)
        response = self.client.post(
            reverse("Project-remove-member", args=[project.id]), data=payload
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert project.get_all_members().count() == 1
        assert to_delete.id not in project.get_all_members()

    def test_remove_members_with_one_owner_org_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        owner = UserFactory()
        project.get_owners().users.clear()
        project.owners.add(owner)
        organization = OrganizationFactory()
        project.organizations.add(organization)

        payload = {
            "users": [owner.keycloak_id],
        }
        user = UserFactory(
            permissions=[
                ("organizations.change_project", organization),
                ("organizations.view_project", organization),
            ]
        )
        self.client.force_authenticate(user)
        response = self.client.post(
            reverse("Project-remove-member", args=(project.id,)), data=payload
        )
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.content
        )
        content = response.json()
        self.assertEqual(
            content["users"],
            {"users": "You cannot remove all the owners of a project."},
        )

    def test_add_linked_projects_org_permission(self):
        project = ProjectFactory()
        owner = UserFactory()
        project.members.add(owner)
        organization = OrganizationFactory()
        project.organizations.add(organization)
        linked_projects = ProjectFactory.create_batch(
            3, publication_status=Project.PublicationStatus.ORG
        )
        for p in linked_projects:
            p.organizations.add(organization)

        payload = {
            "projects": [
                {
                    "project_id": p.id,
                    "target_id": project.id,
                }
                for p in linked_projects
            ]
        }
        user = UserFactory(
            permissions=[
                ("organizations.change_project", organization),
                ("organizations.view_project", organization),
            ]
        )
        self.client.force_authenticate(user)
        response = self.client.post(
            reverse("LinkedProjects-add-many", args=[project.id]), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

        content = response.json()
        self.assertEqual(len(content["linked_projects"]), 3)
        self.assertEqual(
            {p["project"]["id"] for p in content["linked_projects"]},
            {p.id for p in linked_projects},
        )

    def test_update_linked_projects_org_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        linked_project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC
        )
        owner = UserFactory()
        project.members.add(owner)
        linked_project.members.add(owner)
        organization = OrganizationFactory()
        project.organizations.add(organization)
        linked_project.organizations.add(organization)
        link = LinkedProject.objects.create(project=linked_project, target=project)

        user = UserFactory(
            permissions=[
                ("organizations.change_project", organization),
                ("organizations.view_project", organization),
            ]
        )
        self.client.force_authenticate(user)
        response = self.client.patch(
            reverse("LinkedProjects-detail", args=[project.id, link.id])
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

    def test_remove_linked_projects_org_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        linked_project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC
        )
        to_unlinked_project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC
        )
        owner = UserFactory()
        organization = OrganizationFactory()
        project.members.add(owner)
        linked_project.members.add(owner)
        to_unlinked_project.members.add(owner)
        project.organizations.add(organization)
        linked_project.organizations.add(organization)
        to_unlinked_project.organizations.add(organization)
        LinkedProject.objects.create(project=linked_project, target=project)
        LinkedProject.objects.create(project=to_unlinked_project, target=project)

        payload = {"project_ids": [to_unlinked_project.id]}
        user = UserFactory(
            permissions=[
                ("organizations.change_project", organization),
                ("organizations.view_project", organization),
            ]
        )
        self.client.force_authenticate(user)
        response = self.client.delete(
            reverse("LinkedProjects-delete-many", args=(project.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

        content = response.json()
        self.assertEqual(len(content["linked_projects"]), 1)
        self.assertEqual(
            content["linked_projects"][0]["project"]["id"], linked_project.id
        )

    def test_read_linked_projects_org_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        linked_project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC
        )
        linked_project2 = ProjectFactory(
            publication_status=Project.PublicationStatus.PRIVATE
        )
        linked_project3 = ProjectFactory(
            publication_status=Project.PublicationStatus.ORG
        )
        LinkedProject.objects.create(project=linked_project, target=project)
        LinkedProject.objects.create(project=linked_project2, target=project)
        LinkedProject.objects.create(project=linked_project3, target=project)

        organization = linked_project3.organizations.all().first()
        user = UserFactory(
            permissions=[
                ("organizations.change_project", organization),
                ("organizations.view_project", organization),
            ]
        )
        self.client.force_authenticate(user)
        response = self.client.get(reverse("Project-detail", args=(project.id,)))
        linked_projects = response.json()["linked_projects"]
        self.assertEqual(len(linked_projects), 2)
        self.assertEqual(
            sorted(
                [
                    linked_projects[0]["project"]["id"],
                    linked_projects[1]["project"]["id"],
                ]
            ),
            sorted([linked_project.id, linked_project3.id]),
        )


class ProjectFilterTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.test_image = cls.get_test_image()

    def test_filter_category(self):
        category1 = ProjectCategoryFactory()
        category2 = ProjectCategoryFactory()
        category3 = ProjectCategoryFactory()
        project1 = ProjectFactory(header_image=self.test_image, categories=[category1])
        project2 = ProjectFactory(header_image=self.test_image, categories=[category2])
        project3 = ProjectFactory(header_image=self.test_image, categories=[category3])
        ProjectFactory(header_image=self.test_image)
        ProjectFactory(header_image=self.test_image)
        self.client.force_authenticate(UserFactory())
        filters = {"categories": f"{category1.id},{category2.id}"}
        response = self.client.get(reverse("Project-list"), filters)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        content = response.json()
        self.assertEqual(content["count"], 2)
        self.assertEqual(
            {p["id"] for p in content["results"]}, {project1.id, project2.id}
        )
        self.assertTrue(project3.id not in content["results"])

    def test_filter_organization_code(self):
        project1 = ProjectFactory(header_image=self.test_image)
        project2 = ProjectFactory(header_image=self.test_image)
        project3 = ProjectFactory(header_image=self.test_image)
        project4 = ProjectFactory(header_image=self.test_image)
        org1 = OrganizationFactory(code="code1")
        org2 = OrganizationFactory(code="code2")
        org3 = OrganizationFactory(code="code3")
        org4 = OrganizationFactory(code="code4")
        org5 = OrganizationFactory(code="code5", parent=org4)
        project1.organizations.add(org1, org2)
        project2.organizations.add(org2, org3)
        project3.organizations.add(org3, org4)
        project4.organizations.add(org5)

        self.client.force_authenticate(UserFactory())
        filters = {"organizations": f"{org1.code},{org4.code}"}
        response = self.client.get(reverse("Project-list"), filters)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        content = response.json()
        self.assertEqual(content["count"], 3)
        self.assertEqual(
            {p["id"] for p in content["results"]},
            {project1.id, project3.id, project4.id},
        )

    def test_filter_language(self):
        project1 = ProjectFactory(language="fr")
        project2 = ProjectFactory(language="en")
        ProjectFactory(language="ES")
        self.client.force_authenticate(UserFactory())
        filters = {"languages": "fr,en"}
        response = self.client.get(reverse("Project-list"), filters)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        content = response.json()
        self.assertEqual(content["count"], 2)
        self.assertEqual(
            {p["id"] for p in content["results"]}, {project1.id, project2.id}
        )

    def test_filter_members(self):
        project1 = ProjectFactory(header_image=self.test_image)
        project2 = ProjectFactory(header_image=self.test_image)
        project3 = ProjectFactory(header_image=self.test_image)
        user1 = UserFactory()
        user2 = UserFactory()
        user3 = UserFactory()
        user4 = UserFactory()
        project1.members.add(user1, user2)
        project2.members.add(user2, user3)
        project3.members.add(user3, user4)

        self.client.force_authenticate(UserFactory())
        filters = {"members": f"{user1.keycloak_id},{user4.keycloak_id}"}
        response = self.client.get(reverse("Project-list"), filters)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        content = response.json()
        self.assertEqual(content["count"], 2)
        self.assertEqual(
            {p["id"] for p in content["results"]}, {project1.id, project3.id}
        )

    def test_filter_sdgs(self):
        project1 = ProjectFactory(header_image=self.test_image, sdgs=[1, 2])
        project2 = ProjectFactory(header_image=self.test_image, sdgs=[2, 3])
        project3 = ProjectFactory(header_image=self.test_image, sdgs=[3, 4])

        self.client.force_authenticate(UserFactory())
        filters = {"sdgs": "1,4"}
        response = self.client.get(reverse("Project-list"), filters)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        content = response.json()
        self.assertEqual(content["count"], 2)
        self.assertEqual(
            {p["id"] for p in content["results"]}, {project1.id, project3.id}
        )

        filters = {"sdgs": "2,5"}
        response = self.client.get(reverse("Project-list"), filters)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        content = response.json()
        self.assertEqual(content["count"], 2)
        self.assertEqual(
            {p["id"] for p in content["results"]}, {project1.id, project2.id}
        )

        filters = {"sdgs": "2,3"}
        response = self.client.get(reverse("Project-list"), filters)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        content = response.json()
        self.assertEqual(content["count"], 3)
        self.assertEqual(
            {p["id"] for p in content["results"]},
            {project1.id, project2.id, project3.id},
        )

    def test_filter_tags(self):
        project1 = ProjectFactory(header_image=self.test_image)
        project2 = ProjectFactory(header_image=self.test_image)
        project3 = ProjectFactory(header_image=self.test_image)
        tag1 = WikipediaTagFactory(wikipedia_qid="qid1")
        tag2 = WikipediaTagFactory(wikipedia_qid="qid2")
        tag3 = WikipediaTagFactory(wikipedia_qid="qid3")
        tag4 = WikipediaTagFactory(wikipedia_qid="qid4")
        project1.wikipedia_tags.add(tag1, tag2)
        project2.wikipedia_tags.add(tag2, tag3)
        project3.wikipedia_tags.add(tag3, tag4)

        self.client.force_authenticate(UserFactory())
        filters = {"wikipedia_tags": f"{tag1.wikipedia_qid},{tag4.wikipedia_qid}"}
        response = self.client.get(reverse("Project-list"), filters)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        content = response.json()
        self.assertEqual(content["count"], 2)
        self.assertEqual(
            {p["id"] for p in content["results"]}, {project1.id, project3.id}
        )

    def test_filter_member_role(self):
        pc = ProjectCategoryFactory()
        projects = ProjectFactory.create_batch(
            9, header_image=self.get_test_image(), categories=[pc]
        )
        users = UserFactory.create_batch(size=3)

        projects[0].members.add(users[0])
        projects[1].reviewers.add(users[0])
        projects[2].owners.add(users[0])

        projects[3].members.add(users[1])
        projects[4].reviewers.add(users[1])
        projects[5].owners.add(users[1])

        projects[6].members.add(users[2])
        projects[7].reviewers.add(users[2])
        projects[8].owners.add(users[2])

        self.client.force_authenticate(users[0])
        filters = {
            "members": f"{users[0].keycloak_id},{users[1].keycloak_id}",
            "member_role": f"{Project.DefaultGroup.MEMBERS},{Project.DefaultGroup.REVIEWERS}",
        }

        response = self.client.get(reverse("Project-list"), filters)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 4
        self.assertEqual(
            {p["id"] for p in response.data["results"]},
            {projects[0].id, projects[1].id, projects[3].id, projects[4].id},
        )

    def test_filter_life_status(self):
        project1 = ProjectFactory(life_status=Project.LifeStatus.RUNNING)
        project2 = ProjectFactory(life_status=Project.LifeStatus.COMPLETED)
        ProjectFactory(life_status=Project.LifeStatus.TO_REVIEW)

        self.client.force_authenticate(UserFactory())
        filters = {
            "life_status": f"{Project.LifeStatus.RUNNING},{Project.LifeStatus.COMPLETED}"
        }
        response = self.client.get(reverse("Project-list"), filters)
        assert response.status_code == status.HTTP_200_OK
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(
            {p["id"] for p in response.data["results"]}, {project1.id, project2.id}
        )

    def test_filter_creation_year(self):
        project1 = ProjectFactory(header_image=self.test_image)
        project2 = ProjectFactory(header_image=self.test_image)
        project3 = ProjectFactory(header_image=self.test_image)
        project1.created_at = make_aware(datetime.datetime(2020, 1, 1))
        project1.save()
        project2.created_at = make_aware(datetime.datetime(2021, 1, 1))
        project2.save()
        project3.created_at = make_aware(datetime.datetime(2022, 1, 1))
        project3.save()

        self.client.force_authenticate(UserFactory())
        filters = {"creation_year": "2020,2021"}
        response = self.client.get(reverse("Project-list"), filters)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        content = response.json()
        self.assertEqual(content["count"], 2)
        self.assertEqual(
            {p["id"] for p in content["results"]}, {project1.id, project2.id}
        )

    def test_filter_ids_and_slugs(self):
        projects = ProjectFactory.create_batch(5)

        self.client.force_authenticate(UserFactory())
        filters = {"ids": f"{projects[0].id},{projects[1].id},{projects[2].slug}"}
        response = self.client.get(reverse("Project-list"), filters)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        content = response.json()
        self.assertEqual(content["count"], 3)
        self.assertEqual(
            {p["id"] for p in content["results"]},
            {projects[0].id, projects[1].id, projects[2].id},
        )


class ProjectOrderingTestCase(JwtAPITestCase):
    def test_order_by_create_date_ascending(self):
        ProjectFactory()
        ProjectFactory()
        ProjectFactory()
        orderby = {"ordering": "created_at"}
        response = self.client.get(reverse("Project-list"), orderby)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        content = response.json()
        self.assertEqual(content["count"], 3)
        self.assertLess(
            content["results"][0]["created_at"], content["results"][1]["created_at"]
        )
        self.assertLess(
            content["results"][1]["created_at"], content["results"][2]["created_at"]
        )

    def test_order_by_create_date_descending(self):
        ProjectFactory()
        ProjectFactory()
        ProjectFactory()
        orderby = {"ordering": "-created_at"}
        response = self.client.get(reverse("Project-list"), orderby)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        content = response.json()
        self.assertEqual(content["count"], 3)
        self.assertGreater(
            content["results"][0]["created_at"], content["results"][1]["created_at"]
        )
        self.assertGreater(
            content["results"][1]["created_at"], content["results"][2]["created_at"]
        )

    def test_order_by_update_date_ascending(self):
        ProjectFactory()
        ProjectFactory()
        ProjectFactory()
        orderby = {"ordering": "updated_at"}
        response = self.client.get(reverse("Project-list"), orderby)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        content = response.json()
        self.assertEqual(content["count"], 3)
        self.assertLess(
            content["results"][0]["updated_at"], content["results"][1]["updated_at"]
        )
        self.assertLess(
            content["results"][1]["updated_at"], content["results"][2]["updated_at"]
        )

    def test_order_by_update_date_descending(self):
        ProjectFactory()
        ProjectFactory()
        ProjectFactory()
        orderby = {"ordering": "-updated_at"}
        response = self.client.get(reverse("Project-list"), orderby)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        content = response.json()
        self.assertEqual(content["count"], 3)
        self.assertGreater(
            content["results"][0]["updated_at"], content["results"][1]["updated_at"]
        )
        self.assertGreater(
            content["results"][1]["updated_at"], content["results"][2]["updated_at"]
        )


class ProjectTemplateTestCase(ProjectJwtAPITestCase, TagTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.test_image = cls.get_test_image()

    def test_update_category_change_template_superadmin(self):
        user = UserFactory()
        user.groups.add(get_superadmins_group())
        self.client.force_authenticate(user)
        org = OrganizationFactory()
        pc = ProjectCategoryFactory(organization=org)
        ordered_pcs = ProjectCategoryFactory.create_batch(5, organization=org)
        random.shuffle(ordered_pcs)
        ordered_ids = [pc.id for pc in ordered_pcs]
        ordered_template_ids = [pc.template.id for pc in ordered_pcs]
        project = ProjectFactory(organizations=[org], categories=[pc], main_category=pc)
        payload = {
            "project_categories_ids": ordered_ids,
        }
        response = self.client.patch(
            reverse("Project-detail", args=(project.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        content = response.json()
        self.assertEqual(
            content["template"]["id"], ordered_template_ids[0], content["template"]
        )

    def test_update_category_keep_template_superadmin(self):
        user = UserFactory()
        user.groups.add(get_superadmins_group())
        self.client.force_authenticate(user)
        org = OrganizationFactory()
        pc = ProjectCategoryFactory(organization=org)
        ordered_pcs = ProjectCategoryFactory.create_batch(5, organization=org)
        random.shuffle(ordered_pcs)
        ordered_ids = [pc.id for pc in ordered_pcs]
        project = ProjectFactory(organizations=[org], categories=[pc], main_category=pc)
        ordered_ids.append(pc.id)
        payload = {
            "project_categories_ids": ordered_ids,
        }
        response = self.client.patch(
            reverse("Project-detail", args=(project.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        content = response.json()
        self.assertEqual(content["template"]["id"], pc.template.id, content["template"])

    def test_update_no_template_superadmin(self):
        user = UserFactory()
        user.groups.add(get_superadmins_group())
        self.client.force_authenticate(user)
        org = OrganizationFactory()
        ordered_pcs = ProjectCategoryFactory.create_batch(5, organization=org)
        random.shuffle(ordered_pcs)
        ordered_ids = [pc.id for pc in ordered_pcs]
        ordered_template_ids = [pc.template.id for pc in ordered_pcs]
        project = ProjectFactory(organizations=[org])
        payload = {
            "project_categories_ids": ordered_ids,
        }
        response = self.client.patch(
            reverse("Project-detail", args=(project.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        content = response.json()
        self.assertEqual(
            content["template"]["id"], ordered_template_ids[0], content["template"]
        )

    def test_create_superadmin(self):
        user = UserFactory()
        user.groups.add(get_superadmins_group())
        self.client.force_authenticate(user)
        org = OrganizationFactory()
        ordered_pcs = ProjectCategoryFactory.create_batch(5, organization=org)
        random.shuffle(ordered_pcs)
        ordered_ids = [pc.id for pc in ordered_pcs]
        ordered_template_ids = [pc.template.id for pc in ordered_pcs]
        fake = ProjectFactory.build(header_image=self.test_image)
        payload = {
            "title": fake.title,
            "description": fake.description,
            "header_image_id": fake.header_image.id,
            "is_shareable": fake.is_shareable,
            "purpose": fake.purpose,
            "language": fake.language,
            "publication_status": fake.publication_status,
            "life_status": fake.life_status,
            "sdgs": fake.sdgs,
            "project_categories_ids": ordered_ids,
            "organizations_codes": [org.code],
        }
        response = self.client.post(reverse("Project-list"), data=payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.json())
        content = response.json()
        self.assertEqual(
            content["template"]["id"], ordered_template_ids[0], content["template"]
        )


class ProjectUpdatedByReviewerTestCase(ProjectJwtAPITestCase):
    def test_update_status_project_owner(self):
        project = ProjectFactory(
            publication_status=Project.PublicationStatus.PRIVATE,
            categories=[ProjectCategoryFactory(only_reviewer_can_publish=True)],
        )
        user = UserFactory()
        project.owners.add(user)
        self.client.force_authenticate(user)
        payload = {"publication_status": Project.PublicationStatus.PUBLIC}
        response = self.client.patch(
            reverse("Project-detail", args=(project.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json()["publication_status"],
            ["Only a reviewer can change this project's status."],
        )

    def test_update_status_project_reviewer(self):
        project = ProjectFactory(
            publication_status=Project.PublicationStatus.PRIVATE,
            categories=[ProjectCategoryFactory(only_reviewer_can_publish=True)],
        )
        user = UserFactory()
        project.reviewers.add(user)
        self.client.force_authenticate(user)
        payload = {"publication_status": Project.PublicationStatus.PUBLIC}
        response = self.client.patch(
            reverse("Project-detail", args=(project.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json()["publication_status"], Project.PublicationStatus.PUBLIC
        )

    def test_update_status_superadmin(self):
        project = ProjectFactory(
            publication_status=Project.PublicationStatus.PRIVATE,
            categories=[ProjectCategoryFactory(only_reviewer_can_publish=True)],
        )
        user = UserFactory()
        user.groups.add(get_superadmins_group())
        self.client.force_authenticate(user)
        payload = {"publication_status": Project.PublicationStatus.PUBLIC}
        response = self.client.patch(
            reverse("Project-detail", args=(project.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json()["publication_status"], Project.PublicationStatus.PUBLIC
        )

    def test_update_status_org_admin(self):
        organization = OrganizationFactory()
        project = ProjectFactory(
            publication_status=Project.PublicationStatus.PRIVATE,
            organizations=[organization],
            categories=[ProjectCategoryFactory(only_reviewer_can_publish=True)],
        )
        user = UserFactory()
        organization.admins.add(user)
        self.client.force_authenticate(user)
        payload = {"publication_status": Project.PublicationStatus.PUBLIC}
        response = self.client.patch(
            reverse("Project-detail", args=(project.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json()["publication_status"], Project.PublicationStatus.PUBLIC
        )

    def test_update_status_org_facilitator(self):
        organization = OrganizationFactory()
        project = ProjectFactory(
            publication_status=Project.PublicationStatus.PRIVATE,
            organizations=[organization],
            categories=[ProjectCategoryFactory(only_reviewer_can_publish=True)],
        )
        user = UserFactory()
        organization.facilitators.add(user)
        self.client.force_authenticate(user)
        payload = {"publication_status": Project.PublicationStatus.PUBLIC}
        response = self.client.patch(
            reverse("Project-detail", args=(project.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json()["publication_status"], Project.PublicationStatus.PUBLIC
        )


class ProjectUpdatedByReviewerTestCaseAddMember(ProjectJwtAPITestCase):
    def test_add_reviewer_to_public_project(self):
        project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            categories=[ProjectCategoryFactory(only_reviewer_can_publish=True)],
        )
        reviewer = UserFactory()
        payload = {
            Project.DefaultGroup.REVIEWERS: [reviewer.keycloak_id],
        }
        owners = project.get_owners()
        user = UserFactory()
        project.members.add(user)
        owners.users.add(user)
        self.client.force_authenticate(user)
        response = self.client.post(
            reverse("Project-add-member", args=(project.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        project.refresh_from_db()
        self.assertEqual(project.publication_status, Project.PublicationStatus.PRIVATE)

    def test_add_reviewer_to_reviewed_public_project(self):
        project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            categories=[ProjectCategoryFactory(only_reviewer_can_publish=True)],
        )
        project.reviewers.add(UserFactory())
        reviewer = UserFactory()
        payload = {
            Project.DefaultGroup.REVIEWERS: [reviewer.keycloak_id],
        }
        user = UserFactory()
        project.owners.add(user)
        self.client.force_authenticate(user)
        response = self.client.post(
            reverse("Project-add-member", args=(project.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        project.refresh_from_db()
        self.assertEqual(project.publication_status, Project.PublicationStatus.PUBLIC)

    def test_add_owner_and_member_to_public_project(self):
        project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            categories=[ProjectCategoryFactory(only_reviewer_can_publish=True)],
        )
        member = UserFactory()
        owner = UserFactory()
        payload = {
            Project.DefaultGroup.MEMBERS: [member.keycloak_id],
        }
        payload2 = {
            Project.DefaultGroup.OWNERS: [owner.keycloak_id],
        }
        owners = project.get_owners()
        user = UserFactory()
        project.members.add(user)
        owners.users.add(user)
        self.client.force_authenticate(user)
        response = self.client.post(
            reverse("Project-add-member", args=(project.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        response = self.client.post(
            reverse("Project-add-member", args=(project.id,)), data=payload2
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        project.refresh_from_db()
        self.assertEqual(project.publication_status, Project.PublicationStatus.PUBLIC)


class ProjectAddGroupAsMemberTestCase(ProjectJwtAPITestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.organization = OrganizationFactory()
        cls.project = ProjectFactory(
            organizations=[cls.organization],
            publication_status=Project.PublicationStatus.PUBLIC,
            categories=[ProjectCategoryFactory(only_reviewer_can_publish=True)],
        )
        cls.user = UserFactory(
            permissions=[
                ("accounts.view_peoplegroup", None),
                ("accounts.add_peoplegroup", None),
                ("accounts.change_peoplegroup", None),
                ("accounts.delete_peoplegroup", None),
            ]
        )

    def test_add_remove_group_as_member_public_project(self):
        member_group = PeopleGroupFactory(organization=self.organization)
        self.client.force_authenticate(user=self.user)
        payload = {
            Project.DefaultGroup.PEOPLE_GROUPS: [member_group.id],
        }
        self.project.owners.add(self.user)
        response = self.client.post(
            reverse("Project-add-member", args=(self.project.id,)), data=payload
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert member_group in self.project.member_people_groups.all()
        assert all(
            user in self.project.member_people_groups_members.all()
            for user in member_group.get_all_members()
        )

        payload = {
            Project.DefaultGroup.PEOPLE_GROUPS: [member_group.id],
        }
        response = self.client.post(
            reverse("Project-remove-member", args=(self.project.id,)), data=payload
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert member_group not in self.project.member_people_groups.all()
        assert all(
            user not in self.project.member_people_groups_members.all()
            for user in member_group.get_all_members()
        )

    def test_add_already_existing_group_as_member_public_project(self):
        member_group = PeopleGroupFactory(organization=self.organization)
        self.client.force_authenticate(user=self.user)
        payload = {
            Project.DefaultGroup.PEOPLE_GROUPS: [member_group.id],
        }
        self.project.owners.add(self.user)
        self.project.member_people_groups.add(member_group)
        response = self.client.post(
            reverse("Project-add-member", args=(self.project.id,)), data=payload
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert member_group in self.project.member_people_groups.all()

    def test_remove_existing_group_as_member_public_project(self):
        member_group = PeopleGroupFactory(organization=self.organization)
        self.client.force_authenticate(user=self.user)
        payload = {
            Project.DefaultGroup.PEOPLE_GROUPS: [member_group.id],
        }
        self.project.owners.add(self.user)
        self.project.member_people_groups.add(member_group)
        response = self.client.post(
            reverse("Project-remove-member", args=(self.project.id,)), data=payload
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert member_group not in self.project.member_people_groups.all()
        assert all(
            user not in self.project.member_people_groups_members.all()
            for user in member_group.get_all_members()
        )

    def test_remove_non_existing_group_as_member_public_project(self):
        member_group = PeopleGroupFactory(organization=self.organization)
        self.client.force_authenticate(user=self.user)
        payload = {
            Project.DefaultGroup.PEOPLE_GROUPS: [member_group.id],
        }
        self.project.owners.add(self.user)
        response = self.client.post(
            reverse("Project-remove-member", args=(self.project.id,)), data=payload
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT


class ProjectTestCase(ProjectJwtAPITestCase):
    def test_get_slug(self):
        title = "My AMazing TeST ProjeCT !"
        project = ProjectFactory(title=title, deleted_at=now())
        assert project.slug == "my-amazing-test-project"
        project = ProjectFactory(title=title)
        assert project.slug == "my-amazing-test-project-1"
        project = ProjectFactory(title=title)
        assert project.slug == "my-amazing-test-project-2"

    def test_multiple_lookups(self):
        user = UserFactory()
        self.client.force_authenticate(user)
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        response = self.client.get(reverse("Project-detail", args=(project.id,)))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["slug"] == project.slug
        response = self.client.get(reverse("Project-detail", args=(project.slug,)))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == project.id

    def test_reviews_retrieval(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        owner = UserFactory()
        project.members.add(owner)
        reviews = ReviewFactory.create_batch(3, project=project)

        self.client.force_authenticate(owner)
        response = self.client.get(reverse("Project-detail", args=(project.id,)))
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

        content = response.json()
        self.assertEqual(len(content["reviews"]), 3)
        self.assertEqual({r["id"] for r in content["reviews"]}, {r.id for r in reviews})

    def test_locations_retrieval(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        owner = UserFactory()
        project.members.add(owner)
        reviews = LocationFactory.create_batch(3, project=project)

        self.client.force_authenticate(owner)
        response = self.client.get(reverse("Project-detail", args=(project.id,)))
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

        content = response.json()
        self.assertEqual(len(content["locations"]), 3)
        self.assertEqual(
            {r["id"] for r in content["locations"]}, {r.id for r in reviews}
        )

    def test_announcements_retrieval(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        owner = UserFactory()
        project.members.add(owner)
        reviews = AnnouncementFactory.create_batch(3, project=project)

        self.client.force_authenticate(owner)
        response = self.client.get(reverse("Project-detail", args=(project.id,)))
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

        content = response.json()
        self.assertEqual(len(content["announcements"]), 3)
        self.assertEqual(
            {r["id"] for r in content["announcements"]}, {r.id for r in reviews}
        )

    def test_linked_projects_retrieval(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        owner = UserFactory()
        project.members.add(owner)
        linked_projects = ProjectFactory.create_batch(
            3, publication_status=Project.PublicationStatus.PUBLIC
        )
        for p in linked_projects:
            p.members.add(owner)
            LinkedProject.objects.create(project=p, target=project)

        self.client.force_authenticate(owner)
        response = self.client.get(reverse("Project-detail", args=(project.id,)))
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

        content = response.json()
        self.assertEqual(len(content["linked_projects"]), 3)
        self.assertEqual(
            {p["project"]["id"] for p in content["linked_projects"]},
            {p.id for p in linked_projects},
        )

    def test_add_group_member(self):
        project = ProjectFactory()
        owner = UserFactory()
        reviewer = UserFactory()
        member = UserFactory()

        user = UserFactory()
        project.owners.add(user)
        self.client.force_authenticate(user)

        payload = {
            Project.DefaultGroup.OWNERS: [owner.keycloak_id],
            Project.DefaultGroup.REVIEWERS: [reviewer.keycloak_id],
            Project.DefaultGroup.MEMBERS: [member.keycloak_id],
        }
        response = self.client.post(
            reverse("Project-add-member", args=(project.id,)), data=payload
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert owner in project.owners.all()
        assert reviewer in project.reviewers.all()
        assert member in project.members.all()

    def test_change_member_role(self):
        project = ProjectFactory()
        user = UserFactory()
        to_update = UserFactory()
        project.owners.add(user)
        project.members.add(user, to_update)
        self.client.force_authenticate(user)

        payload = {
            Project.DefaultGroup.OWNERS: [to_update.keycloak_id],
        }
        response = self.client.post(
            reverse("Project-add-member", args=[project.id]), data=payload
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert to_update in project.owners.all()
        assert to_update not in project.members.all()

    def test_remove_group_member(self):
        project = ProjectFactory()

        owner = UserFactory()
        reviewer = UserFactory()
        member = UserFactory()

        project.owners.add(owner)
        project.reviewers.add(reviewer)
        project.members.add(member)

        user = UserFactory()
        project.owners.add(user)
        self.client.force_authenticate(user)

        payload = {
            "users": [owner.keycloak_id, member.keycloak_id, reviewer.keycloak_id],
        }
        response = self.client.post(
            reverse("Project-remove-member", args=(project.id,)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertNotIn(owner, project.get_all_members())
        self.assertNotIn(member, project.get_all_members())
        self.assertNotIn(reviewer, project.get_all_members())

    def test_is_followed_get(self):
        project = ProjectFactory()
        user = UserFactory()
        self.client.force_authenticate(user)

        response = self.client.get(reverse("Project-detail", args=(project.id,)))
        assert response.status_code == 200
        assert response.json()["is_followed"]["is_followed"] is False

        follow = FollowFactory(follower=user, project=project)
        response = self.client.get(reverse("Project-detail", args=(project.id,)))
        assert response.status_code == 200
        assert response.json()["is_followed"]["is_followed"] is True
        assert response.json()["is_followed"]["follow_id"] == follow.id

    def test_is_followed_list(self):
        projects = ProjectFactory.create_batch(10)
        user = UserFactory()
        follow_1 = FollowFactory(follower=user, project=projects[0])
        follow_2 = FollowFactory(follower=user, project=projects[1])
        self.client.force_authenticate(user)

        response = self.client.get(reverse("Project-list"))
        assert response.status_code == 200
        content = response.json()["results"]
        followed = {
            p["id"]
            for p in list(filter(lambda x: x["is_followed"]["is_followed"], content))
        }
        assert followed == {projects[0].id, projects[1].id}
        follow_ids = {
            p["is_followed"]["follow_id"]
            for p in list(filter(lambda x: x["is_followed"]["is_followed"], content))
        }
        assert follow_ids == {follow_1.id, follow_2.id}

    def test_create_with_members(self):
        fake = ProjectFactory.build()
        organization = OrganizationFactory()
        category = ProjectCategoryFactory(organization=organization)
        members = UserFactory.create_batch(3)
        reviewers = UserFactory.create_batch(3)
        owners = UserFactory.create_batch(3)
        organization_tags = TagFactory.create_batch(3, organization=organization)
        payload = {
            "organizations_codes": [organization.code],
            "title": fake.title,
            "description": fake.description,
            "header_image": self.get_test_image_file(),
            "is_shareable": fake.is_shareable,
            "purpose": fake.purpose,
            "language": fake.language,
            "publication_status": fake.publication_status,
            "life_status": fake.life_status,
            "sdgs": fake.sdgs,
            "project_categories_ids": [category.id],
            "organization_tags_ids": [t.id for t in organization_tags],
            "images_ids": [],
            "team": {
                "members": [m.keycloak_id for m in members],
                "reviewers": [r.keycloak_id for r in reviewers],
                "owners": [o.keycloak_id for o in owners],
            },
        }
        user = UserFactory()
        self.client.force_authenticate(user)
        response = self.client.post(
            reverse("Project-list"),
            data=encode_multipart(data=payload, boundary=BOUNDARY),
            content_type=MULTIPART_CONTENT,
        )
        assert response.status_code == status.HTTP_201_CREATED
        project = Project.objects.get(id=response.data["id"])
        assert user in project.owners.all()

    @patch(target="services.recsys.interface.RecsysService.get_similar_projects")
    def test_get_similar_projects(self, mocked):
        projects = ProjectFactory.create_batch(
            6, publication_status=Project.PublicationStatus.PUBLIC
        )
        mock_response = {
            project.id: round(random.uniform(0.0, 10.0), 3)  # nosec
            for project in projects
        }
        mocked.side_effect = lambda x, y, z: mock_response
        response = self.client.get(reverse("Project-similar", args=(projects[0].id,)))
        assert response.status_code == 200
        content = response.json()
        assert len(content) == 5  # Project from request is filtered
        for i in range(4):
            assert (
                mock_response[content[i]["id"]] >= mock_response[content[i + 1]["id"]]
            )
