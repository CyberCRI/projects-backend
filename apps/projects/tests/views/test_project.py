import datetime
import random
from typing import Dict
from unittest.mock import patch

from django.urls import reverse
from django.utils.timezone import make_aware, now
from faker import Faker
from parameterized import parameterized
from rest_framework import status

from apps.accounts.factories import PeopleGroupFactory, UserFactory
from apps.accounts.utils import get_superadmins_group
from apps.announcements.factories import AnnouncementFactory
from apps.commons.test import JwtAPITestCase, TestRoles
from apps.commons.test.testcases import TagTestCaseMixin
from apps.feedbacks.factories import FollowFactory
from apps.files.factories import AttachmentFileFactory, AttachmentLinkFactory
from apps.goals.factories import GoalFactory
from apps.misc.factories import TagFactory, WikipediaTagFactory
from apps.misc.models import SDG, Language
from apps.organizations.factories import OrganizationFactory, ProjectCategoryFactory
from apps.projects.factories import BlogEntryFactory, ProjectFactory
from apps.projects.models import Project

faker = Faker()


class CreateProjectTestCase(JwtAPITestCase, TagTestCaseMixin):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.category = ProjectCategoryFactory(organization=cls.organization)
        cls.members = UserFactory.create_batch(2)
        cls.reviewers = UserFactory.create_batch(2)
        cls.owners = UserFactory.create_batch(2)
        cls.people_groups = PeopleGroupFactory.create_batch(
            2, organization=cls.organization
        )
        cls.organization_tags = TagFactory.create_batch(
            3, organization=cls.organization
        )
        cls.wikipedia_tags = WikipediaTagFactory.create_batch(3)

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_201_CREATED),
            (TestRoles.SUPERADMIN, status.HTTP_201_CREATED),
            (TestRoles.ORG_ADMIN, status.HTTP_201_CREATED),
            (TestRoles.ORG_FACILITATOR, status.HTTP_201_CREATED),
            (TestRoles.ORG_USER, status.HTTP_201_CREATED),
        ]
    )
    @patch("apps.misc.api.get_tag_from_wikipedia_gw")
    def test_create_project(self, role, expected_code, mocked):
        mocked.side_effect = self.get_wikipedia_tag_mocked_side_effect
        user = self.get_parameterized_test_user(role, instances=[self.organization])
        self.client.force_authenticate(user)
        payload = {
            "organizations_codes": [self.organization.code],
            "title": faker.sentence(),
            "description": faker.text(),
            "is_shareable": faker.boolean(),
            "purpose": faker.sentence(),
            "language": random.choice(Language.values),  # nosec
            "publication_status": random.choice(
                Project.PublicationStatus.values
            ),  # nosec
            "life_status": random.choice(Project.LifeStatus.values),  # nosec
            "sdgs": random.choices(SDG.values, k=3),  # nosec
            "project_categories_ids": [self.category.id],
            "organization_tags_ids": [t.id for t in self.organization_tags],
            "wikipedia_tags_ids": [t.wikipedia_qid for t in self.wikipedia_tags],
            "images_ids": [],
            "team": {
                "members": [m.id for m in self.members],
                "reviewers": [r.id for r in self.reviewers],
                "owners": [o.id for o in self.owners],
                "people_groups": [pg.id for pg in self.people_groups],
            },
        }
        response = self.client.post(reverse("Project-list"), data=payload)
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_201_CREATED:
            content = response.json()
            self.assertEqual(content["title"], payload["title"])
            self.assertEqual(content["description"], payload["description"])
            self.assertEqual(content["is_shareable"], payload["is_shareable"])
            self.assertEqual(content["purpose"], payload["purpose"])
            self.assertEqual(content["language"], payload["language"])
            self.assertEqual(
                content["publication_status"], payload["publication_status"]
            )
            self.assertEqual(content["life_status"], payload["life_status"])
            self.assertEqual(content["sdgs"], payload["sdgs"])
            self.assertEqual(
                {o["code"] for o in content["organizations"]},
                set(payload["organizations_codes"]),
            )
            self.assertEqual(
                {c["id"] for c in content["categories"]},
                set(payload["project_categories_ids"]),
            )
            self.assertEqual(
                {t["id"] for t in content["organization_tags"]},
                set(payload["organization_tags_ids"]),
            )
            self.assertEqual(
                {t["wikipedia_qid"] for t in content["wikipedia_tags"]},
                set(payload["wikipedia_tags_ids"]),
            )
            self.assertEqual(
                {u["id"] for u in content["team"]["members"]},
                set(payload["team"]["members"]),
            )
            self.assertEqual(
                {u["id"] for u in content["team"]["reviewers"]},
                set(payload["team"]["reviewers"]),
            )
            self.assertEqual(
                {u["id"] for u in content["team"]["owners"]},
                {user.id, *payload["team"]["owners"]},
            )
            self.assertEqual(
                {u["id"] for u in content["team"]["people_groups"]},
                set(payload["team"]["people_groups"]),
            )


class UpdateProjectTestCase(JwtAPITestCase, TagTestCaseMixin):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.category = ProjectCategoryFactory(
            organization=cls.organization,
            is_reviewable=True,
            only_reviewer_can_publish=True,
        )
        cls.organization_tags = TagFactory.create_batch(
            3, organization=cls.organization
        )
        cls.wikipedia_tags = WikipediaTagFactory.create_batch(3)

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_ADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_FACILITATOR, status.HTTP_200_OK),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_MEMBER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_OWNER, status.HTTP_200_OK),
            (TestRoles.PROJECT_REVIEWER, status.HTTP_200_OK),
        ]
    )
    @patch("apps.misc.api.get_tag_from_wikipedia_gw")
    def test_update_project(self, role, expected_code, mocked):
        mocked.side_effect = self.get_wikipedia_tag_mocked_side_effect
        project = ProjectFactory(organizations=[self.organization])
        user = self.get_parameterized_test_user(role, instances=[project])
        self.client.force_authenticate(user)
        payload = {
            "title": faker.sentence(),
            "description": faker.text(),
            "is_shareable": faker.boolean(),
            "purpose": faker.sentence(),
            "language": random.choice(Language.values),  # nosec
            "publication_status": random.choice(
                Project.PublicationStatus.values
            ),  # nosec
            "life_status": random.choice(Project.LifeStatus.values),  # nosec
            "sdgs": random.choices(SDG.values, k=3),  # nosec
            "organization_tags_ids": [
                random.choice(self.organization_tags).id  # nosec
            ],
            "wikipedia_tags_ids": [
                random.choice(self.wikipedia_tags).wikipedia_qid  # nosec
            ],
        }
        response = self.client.patch(
            reverse("Project-detail", args=(project.id,)), data=payload
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_200_OK:
            content = response.json()
            self.assertEqual(content["title"], payload["title"])
            self.assertEqual(content["description"], payload["description"])
            self.assertEqual(content["is_shareable"], payload["is_shareable"])
            self.assertEqual(content["purpose"], payload["purpose"])
            self.assertEqual(content["language"], payload["language"])
            self.assertEqual(
                content["publication_status"], payload["publication_status"]
            )
            self.assertEqual(content["life_status"], payload["life_status"])
            self.assertEqual(content["sdgs"], payload["sdgs"])
            self.assertEqual(
                {t["id"] for t in content["organization_tags"]},
                set(payload["organization_tags_ids"]),
            )
            self.assertEqual(
                {t["wikipedia_qid"] for t in content["wikipedia_tags"]},
                set(payload["wikipedia_tags_ids"]),
            )

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_ADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_FACILITATOR, status.HTTP_200_OK),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_MEMBER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_OWNER, status.HTTP_400_BAD_REQUEST),
            (TestRoles.PROJECT_REVIEWER, status.HTTP_200_OK),
        ]
    )
    def test_update_project_only_reviewer_can_update(self, role, expected_code):
        project = ProjectFactory(
            organizations=[self.organization],
            categories=[self.category],
            main_category=self.category,
            publication_status=Project.PublicationStatus.PRIVATE,
            life_status=Project.LifeStatus.TO_REVIEW,
        )
        user = self.get_parameterized_test_user(role, instances=[project])
        self.client.force_authenticate(user)
        payload = {
            "publication_status": Project.PublicationStatus.PUBLIC,
        }
        response = self.client.patch(
            reverse("Project-detail", args=(project.id,)), data=payload
        )
        self.assertEqual(response.status_code, expected_code)
        content = response.json()
        if expected_code == status.HTTP_200_OK:
            self.assertEqual(
                content["publication_status"], payload["publication_status"]
            )
        if expected_code == status.HTTP_400_BAD_REQUEST:
            self.assertEqual(
                content["publication_status"],
                ["Only a reviewer can change this project's status."],
            )

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_ADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_FACILITATOR, status.HTTP_200_OK),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_MEMBER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_OWNER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_REVIEWER, status.HTTP_200_OK),
        ]
    )
    def test_update_locked_project(self, role, expected_code):
        project = ProjectFactory(is_locked=True)
        user = self.get_parameterized_test_user(role, instances=[project])
        self.client.force_authenticate(user)
        payload = {
            "title": faker.sentence(),
        }
        response = self.client.patch(
            reverse("Project-detail", args=(project.id,)),
            data=payload,
        )
        self.assertEqual(response.status_code, expected_code)


class DeleteProjectTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_ADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_FACILITATOR, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_MEMBER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_OWNER, status.HTTP_204_NO_CONTENT),
            (TestRoles.PROJECT_REVIEWER, status.HTTP_204_NO_CONTENT),
        ]
    )
    def test_delete_project(self, role, expected_code):
        project = ProjectFactory(organizations=[self.organization])
        user = self.get_parameterized_test_user(role, instances=[project])
        self.client.force_authenticate(user)
        response = self.client.delete(reverse("Project-detail", args=(project.id,)))
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_204_NO_CONTENT:
            project.refresh_from_db()
            self.assertFalse(Project.objects.filter(id=project.id).exists())
            self.assertIsNotNone(project.deleted_at)


class ProjectMembersTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.members = UserFactory.create_batch(2)
        cls.owners = UserFactory.create_batch(2)
        cls.reviewers = UserFactory.create_batch(2)
        cls.people_groups = PeopleGroupFactory.create_batch(
            2, organization=cls.organization
        )

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_ADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_FACILITATOR, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_MEMBER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_OWNER, status.HTTP_204_NO_CONTENT),
            (TestRoles.PROJECT_REVIEWER, status.HTTP_204_NO_CONTENT),
        ]
    )
    def test_add_project_member(self, role, expected_code):
        project = ProjectFactory(organizations=[self.organization])
        user = self.get_parameterized_test_user(role, instances=[project])
        self.client.force_authenticate(user)
        payload = {
            "members": [m.id for m in self.members],
            "owners": [r.id for r in self.owners],
            "reviewers": [r.id for r in self.reviewers],
            "people_groups": [pg.id for pg in self.people_groups],
        }
        response = self.client.post(
            reverse("Project-add-member", args=(project.id,)),
            data=payload,
        )
        assert response.status_code == expected_code
        if expected_code == status.HTTP_204_NO_CONTENT:
            assert all(member in project.members.all() for member in self.members)
            assert all(owner in project.owners.all() for owner in self.owners)
            assert all(
                reviewer in project.reviewers.all() for reviewer in self.reviewers
            )
            assert all(
                people_group in project.member_people_groups.all()
                for people_group in self.people_groups
            )

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_ADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_FACILITATOR, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_MEMBER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_OWNER, status.HTTP_204_NO_CONTENT),
            (TestRoles.PROJECT_REVIEWER, status.HTTP_204_NO_CONTENT),
        ]
    )
    def test_remove_project_member(self, role, expected_code):
        project = ProjectFactory(organizations=[self.organization])
        project.members.add(*self.members)
        project.owners.add(*self.owners)
        project.reviewers.add(*self.reviewers)
        project.member_people_groups.add(*self.people_groups)
        user = self.get_parameterized_test_user(role, instances=[project])
        self.client.force_authenticate(user)
        payload = {
            "users": [u.id for u in self.members + self.owners + self.reviewers],
            "people_groups": [pg.id for pg in self.people_groups],
        }
        response = self.client.post(
            reverse("Project-remove-member", args=(project.id,)),
            data=payload,
        )
        assert response.status_code == expected_code
        if expected_code == status.HTTP_204_NO_CONTENT:
            assert all(member not in project.members.all() for member in self.members)
            assert all(owner not in project.owners.all() for owner in self.owners)
            assert all(
                reviewer not in project.reviewers.all() for reviewer in self.reviewers
            )
            assert all(
                people_group not in project.member_people_groups.all()
                for people_group in self.people_groups
            )

    def test_remove_project_member_self(self):
        project = ProjectFactory(organizations=[self.organization])
        to_delete = UserFactory()
        project.members.add(to_delete)
        self.client.force_authenticate(to_delete)
        response = self.client.delete(
            reverse("Project-remove-self", args=(project.id,))
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert to_delete not in project.members.all()


class DuplicateProjectTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.category = ProjectCategoryFactory(organization=cls.organization)
        cls.project = ProjectFactory(
            publication_status=Project.PublicationStatus.PRIVATE,
            organizations=[cls.organization],
            categories=[cls.category],
            header_image=cls.get_test_image(),
        )
        blog_entries = BlogEntryFactory.create_batch(3, project=cls.project)
        GoalFactory.create_batch(3, project=cls.project)
        AttachmentLinkFactory.create_batch(3, project=cls.project)
        AttachmentFileFactory.create_batch(3, project=cls.project)
        AnnouncementFactory.create_batch(3, project=cls.project)
        images = [cls.get_test_image() for _ in range(3)]
        cls.project.images.set(images)
        cls.project.description = "\n".join(
            [
                f'<img src="/v1/project/{cls.project.pk}/image/{i.pk}/" />'
                for i in images
            ]
        )
        cls.project.save()
        blog_entries_images = [cls.get_test_image() for _ in range(3)]
        blog_entries[0].images.add(*blog_entries_images)
        blog_entries[0].content = "\n".join(
            [
                f'<img src="/v1/project/{cls.project.pk}/blog-entry-image/{i.pk}/" />'
                for i in blog_entries_images
            ]
        )
        blog_entries[0].save()

    @classmethod
    def check_duplicated_project(cls, duplicated_project: Dict, initial_project: Dict):
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

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_201_CREATED),
            (TestRoles.ORG_ADMIN, status.HTTP_201_CREATED),
            (TestRoles.ORG_FACILITATOR, status.HTTP_201_CREATED),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_MEMBER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_OWNER, status.HTTP_201_CREATED),
            (TestRoles.PROJECT_REVIEWER, status.HTTP_201_CREATED),
        ]
    )
    def test_duplicate_project(self, role, expected_code):
        user = self.get_parameterized_test_user(role, instances=[self.project])
        self.client.force_authenticate(user)
        response = self.client.post(
            reverse("Project-duplicate", args=(self.project.id,))
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_201_CREATED:
            initial_response = self.client.get(
                reverse("Project-detail", args=(self.project.id,))
            )
            self.assertEqual(initial_response.status_code, status.HTTP_200_OK)
            duplicated_project = response.json()
            initial_project = initial_response.json()
            self.check_duplicated_project(duplicated_project, initial_project)


class LockUnlockProjectTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_ADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_FACILITATOR, status.HTTP_200_OK),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_MEMBER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_OWNER, status.HTTP_200_OK),
            (TestRoles.PROJECT_REVIEWER, status.HTTP_200_OK),
        ]
    )
    def test_lock_project(self, role, expected_code):
        project = ProjectFactory(organizations=[self.organization], is_locked=False)
        user = self.get_parameterized_test_user(role, instances=[project])
        self.client.force_authenticate(user)
        response = self.client.post(reverse("Project-lock", args=(project.id,)))
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_200_OK:
            project.refresh_from_db()
            self.assertTrue(project.is_locked)

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_ADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_FACILITATOR, status.HTTP_200_OK),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_MEMBER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_OWNER, status.HTTP_200_OK),
            (TestRoles.PROJECT_REVIEWER, status.HTTP_200_OK),
        ]
    )
    def test_unlock_project(self, role, expected_code):
        project = ProjectFactory(organizations=[self.organization], is_locked=True)
        user = self.get_parameterized_test_user(role, instances=[project])
        self.client.force_authenticate(user)
        response = self.client.post(reverse("Project-unlock", args=(project.id,)))
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_200_OK:
            project.refresh_from_db()
            self.assertFalse(project.is_locked)


class FilterSearchOrderProjectTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization_1 = OrganizationFactory()
        cls.organization_2 = OrganizationFactory()
        cls.organization_3 = OrganizationFactory(parent=cls.organization_1)
        cls.category_1 = ProjectCategoryFactory(organization=cls.organization_1)
        cls.category_2 = ProjectCategoryFactory(organization=cls.organization_2)
        cls.category_3 = ProjectCategoryFactory(organization=cls.organization_3)
        cls.tag_1 = WikipediaTagFactory()
        cls.tag_2 = WikipediaTagFactory()
        cls.tag_3 = WikipediaTagFactory()
        cls.date_1 = make_aware(datetime.datetime(2020, 1, 1))
        cls.date_2 = make_aware(datetime.datetime(2021, 1, 1))
        cls.date_3 = make_aware(datetime.datetime(2022, 1, 1))

        cls.project_1 = ProjectFactory(
            organizations=[cls.organization_1],
            categories=[cls.category_1],
            main_category=cls.category_1,
            language="fr",
            sdgs=[1, 2],
            life_status=Project.LifeStatus.TO_REVIEW,
        )
        cls.project_2 = ProjectFactory(
            organizations=[cls.organization_2],
            categories=[cls.category_2],
            main_category=cls.category_2,
            language="en",
            sdgs=[2, 3],
            life_status=Project.LifeStatus.RUNNING,
        )
        cls.project_3 = ProjectFactory(
            organizations=[cls.organization_3],
            categories=[cls.category_3],
            main_category=cls.category_3,
            language="en",
            sdgs=[3, 4],
            life_status=Project.LifeStatus.COMPLETED,
        )
        cls.project_1.wikipedia_tags.add(cls.tag_1, cls.tag_2)
        cls.project_2.wikipedia_tags.add(cls.tag_2, cls.tag_3)
        cls.project_3.wikipedia_tags.add(cls.tag_3)
        cls.user_1 = UserFactory(
            groups=[cls.project_1.get_owners(), cls.project_2.get_reviewers()]
        )
        cls.user_2 = UserFactory(
            groups=[cls.project_2.get_members(), cls.project_3.get_reviewers()]
        )
        cls.user_3 = UserFactory(
            groups=[cls.project_2.get_owners(), cls.project_3.get_owners()]
        )
        Project.objects.filter(id=cls.project_1.id).update(
            created_at=cls.date_1,
            updated_at=cls.date_1,
        )
        Project.objects.filter(id=cls.project_2.id).update(
            created_at=cls.date_2,
            updated_at=cls.date_2,
        )
        Project.objects.filter(id=cls.project_3.id).update(
            created_at=cls.date_3,
            updated_at=cls.date_3,
        )
        cls.superadmin = UserFactory(groups=[get_superadmins_group()])

    def test_filter_category(self):
        self.client.force_authenticate(self.superadmin)
        filters = {"categories": f"{self.category_1.id},{self.category_2.id}"}
        response = self.client.get(reverse("Project-list"), filters)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        content = response.json()
        self.assertEqual(content["count"], 2)
        self.assertEqual(
            {p["id"] for p in content["results"]},
            {self.project_1.id, self.project_2.id},
        )

    def test_filter_organization_code(self):
        self.client.force_authenticate(self.superadmin)
        filters = {"organizations": f"{self.organization_1.code}"}
        response = self.client.get(reverse("Project-list"), filters)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        content = response.json()
        self.assertEqual(content["count"], 2)
        self.assertEqual(
            {p["id"] for p in content["results"]},
            {self.project_1.id, self.project_3.id},
        )

    def test_filter_language(self):
        self.client.force_authenticate(UserFactory())
        filters = {"languages": "en"}
        response = self.client.get(reverse("Project-list"), filters)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        content = response.json()
        self.assertEqual(content["count"], 2)
        self.assertEqual(
            {p["id"] for p in content["results"]},
            {self.project_2.id, self.project_3.id},
        )

    def test_filter_members(self):
        self.client.force_authenticate(UserFactory())
        filters = {"members": f"{self.user_2.keycloak_id},{self.user_3.keycloak_id}"}
        response = self.client.get(reverse("Project-list"), filters)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        content = response.json()
        self.assertEqual(content["count"], 2)
        self.assertEqual(
            {p["id"] for p in content["results"]},
            {self.project_2.id, self.project_3.id},
        )

    def test_filter_sdgs(self):
        self.client.force_authenticate(UserFactory())
        filters = {"sdgs": "1,4,7"}
        response = self.client.get(reverse("Project-list"), filters)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        content = response.json()
        self.assertEqual(content["count"], 2)
        self.assertEqual(
            {p["id"] for p in content["results"]},
            {self.project_1.id, self.project_3.id},
        )

    def test_filter_tags(self):
        self.client.force_authenticate(UserFactory())
        filters = {
            "wikipedia_tags": f"{self.tag_1.wikipedia_qid},{self.tag_2.wikipedia_qid}"
        }
        response = self.client.get(reverse("Project-list"), filters)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        content = response.json()
        self.assertEqual(content["count"], 2)
        self.assertEqual(
            {p["id"] for p in content["results"]},
            {self.project_1.id, self.project_2.id},
        )

    def test_filter_member_role(self):
        self.client.force_authenticate(self.superadmin)
        filters = {
            "members": f"{self.user_1.keycloak_id},{self.user_2.keycloak_id}",
            "member_role": f"{Project.DefaultGroup.OWNERS},{Project.DefaultGroup.MEMBERS}",
        }

        response = self.client.get(reverse("Project-list"), filters)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["count"] == 2
        self.assertEqual(
            {p["id"] for p in response.data["results"]},
            {self.project_1.id, self.project_2.id},
        )

    def test_filter_life_status(self):
        self.client.force_authenticate(UserFactory())
        filters = {
            "life_status": f"{Project.LifeStatus.RUNNING},{Project.LifeStatus.COMPLETED}"
        }
        response = self.client.get(reverse("Project-list"), filters)
        assert response.status_code == status.HTTP_200_OK
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(
            {p["id"] for p in response.data["results"]},
            {self.project_2.id, self.project_3.id},
        )

    def test_filter_creation_year(self):
        self.client.force_authenticate(UserFactory())
        filters = {"creation_year": "2020,2021"}
        response = self.client.get(reverse("Project-list"), filters)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        content = response.json()
        self.assertEqual(content["count"], 2)
        self.assertEqual(
            {p["id"] for p in content["results"]},
            {self.project_1.id, self.project_2.id},
        )

    def test_filter_ids_and_slugs(self):
        self.client.force_authenticate(UserFactory())
        filters = {"ids": f"{self.project_1.id},{self.project_2.slug}"}
        response = self.client.get(reverse("Project-list"), filters)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        content = response.json()
        self.assertEqual(content["count"], 2)
        self.assertEqual(
            {p["id"] for p in content["results"]},
            {self.project_1.id, self.project_2.id},
        )

    def test_order_by_create_date_ascending(self):
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


class ValidateProjectTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.superadmin = UserFactory(groups=[get_superadmins_group()])

    def test_update_without_organization(self):
        self.client.force_authenticate(self.superadmin)
        project = ProjectFactory(organizations=[self.organization])
        payload = {"organizations_codes": []}
        response = self.client.patch(
            reverse("Project-detail", args=(project.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("organizations_codes", response.data)

    def test_remove_last_member(self):
        self.client.force_authenticate(self.superadmin)
        project = ProjectFactory(organizations=[self.organization])
        owner = project.owners.first()
        payload = {
            "users": [owner.keycloak_id],
        }
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


class MiscProjectTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.superadmin = UserFactory(groups=[get_superadmins_group()])

    def test_get_slug(self):
        title = "My AMazing TeST ProjeCT !"
        project = ProjectFactory(
            organizations=[self.organization], title=title, deleted_at=now()
        )
        assert project.slug == "my-amazing-test-project"
        project = ProjectFactory(organizations=[self.organization], title=title)
        assert project.slug == "my-amazing-test-project-1"
        project = ProjectFactory(organizations=[self.organization], title=title)
        assert project.slug == "my-amazing-test-project-2"

    def test_multiple_lookups(self):
        project = ProjectFactory(
            organizations=[self.organization],
            publication_status=Project.PublicationStatus.PUBLIC,
        )
        response = self.client.get(reverse("Project-detail", args=(project.id,)))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["slug"] == project.slug
        response = self.client.get(reverse("Project-detail", args=(project.slug,)))
        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == project.id

    def test_change_member_role(self):
        self.client.force_authenticate(self.superadmin)
        project = ProjectFactory(organizations=[self.organization])
        user = UserFactory(groups=[project.get_members()])
        payload = {
            Project.DefaultGroup.OWNERS: [user.id],
        }
        response = self.client.post(
            reverse("Project-add-member", args=[project.id]), data=payload
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert user in project.owners.all()
        assert user not in project.members.all()

    def test_is_followed_get(self):
        project = ProjectFactory(organizations=[self.organization])
        user = self.superadmin
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
        projects = ProjectFactory.create_batch(3, organizations=[self.organization])
        user = self.superadmin
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

    def test_add_reviewer_to_public_project(self):
        self.client.force_authenticate(self.superadmin)
        project = ProjectFactory(
            organizations=[self.organization],
            categories=[ProjectCategoryFactory(only_reviewer_can_publish=True)],
        )
        reviewer = UserFactory()
        payload = {
            Project.DefaultGroup.REVIEWERS: [reviewer.keycloak_id],
        }
        response = self.client.post(
            reverse("Project-add-member", args=(project.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        project.refresh_from_db()
        self.assertEqual(project.publication_status, Project.PublicationStatus.PRIVATE)

    def test_add_reviewer_to_reviewed_public_project(self):
        self.client.force_authenticate(self.superadmin)
        project = ProjectFactory(
            organizations=[self.organization],
            categories=[ProjectCategoryFactory(only_reviewer_can_publish=True)],
        )
        UserFactory(groups=[project.get_reviewers()])
        reviewer = UserFactory()
        payload = {
            Project.DefaultGroup.REVIEWERS: [reviewer.keycloak_id],
        }
        response = self.client.post(
            reverse("Project-add-member", args=(project.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        project.refresh_from_db()
        self.assertEqual(project.publication_status, Project.PublicationStatus.PUBLIC)

    def test_update_category_change_template_superadmin(self):
        self.client.force_authenticate(self.superadmin)
        category = ProjectCategoryFactory(organization=self.organization)
        categories = ProjectCategoryFactory.create_batch(
            3, organization=self.organization
        )
        project = ProjectFactory(
            organizations=[self.organization],
            categories=[category],
            main_category=category,
        )
        payload = {
            "project_categories_ids": [pc.id for pc in categories],
        }
        response = self.client.patch(
            reverse("Project-detail", args=(project.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["template"]["id"], categories[0].template.id)

    def test_update_category_keep_template_superadmin(self):
        self.client.force_authenticate(self.superadmin)
        category = ProjectCategoryFactory(organization=self.organization)
        categories = ProjectCategoryFactory.create_batch(
            3, organization=self.organization
        )
        project = ProjectFactory(
            organizations=[self.organization],
            categories=[category],
            main_category=category,
        )
        payload = {
            "project_categories_ids": [*[pc.id for pc in categories], category.id],
        }
        response = self.client.patch(
            reverse("Project-detail", args=(project.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        content = response.json()
        self.assertEqual(content["template"]["id"], category.template.id)

    def test_update_no_template_superadmin(self):
        self.client.force_authenticate(self.superadmin)
        categories = ProjectCategoryFactory.create_batch(
            3, organization=self.organization
        )
        project = ProjectFactory(organizations=[self.organization])
        payload = {
            "project_categories_ids": [pc.id for pc in categories],
        }
        response = self.client.patch(
            reverse("Project-detail", args=(project.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        content = response.json()
        self.assertEqual(content["template"]["id"], categories[0].template.id)
