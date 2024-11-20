import datetime
import random
from typing import Dict

from django.urls import reverse
from django.utils import timezone
from django.utils.timezone import make_aware
from faker import Faker
from parameterized import parameterized
from rest_framework import status

from apps.accounts.factories import PeopleGroupFactory, UserFactory
from apps.accounts.utils import get_superadmins_group
from apps.announcements.factories import AnnouncementFactory
from apps.commons.models import SDG, Language
from apps.commons.test import JwtAPITestCase, TestRoles
from apps.feedbacks.factories import FollowFactory
from apps.files.factories import AttachmentFileFactory, AttachmentLinkFactory
from apps.organizations.factories import OrganizationFactory, ProjectCategoryFactory
from apps.projects.factories import BlogEntryFactory, GoalFactory, ProjectFactory
from apps.projects.models import Project
from apps.skills.factories import TagFactory

faker = Faker()


class CreateProjectTestCase(JwtAPITestCase):
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
        cls.tags = TagFactory.create_batch(3)

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_201_CREATED),
            (TestRoles.ORG_ADMIN, status.HTTP_201_CREATED),
            (TestRoles.ORG_FACILITATOR, status.HTTP_201_CREATED),
            (TestRoles.ORG_USER, status.HTTP_201_CREATED),
        ]
    )
    def test_create_project(self, role, expected_code):
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
            "tags": [t.id for t in self.tags],
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
                {t["id"] for t in content["tags"]},
                set(payload["tags"]),
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


class UpdateProjectTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.category = ProjectCategoryFactory(
            organization=cls.organization,
            is_reviewable=True,
            only_reviewer_can_publish=True,
        )
        cls.tags = TagFactory.create_batch(3)
        cls.project = ProjectFactory(organizations=[cls.organization])

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
    def test_update_project(self, role, expected_code):
        user = self.get_parameterized_test_user(role, instances=[self.project])
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
            "tags": [random.choice(self.tags).id],  # nosec
        }
        response = self.client.patch(
            reverse("Project-detail", args=(self.project.id,)), data=payload
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
                {t["id"] for t in content["tags"]},
                set(payload["tags"]),
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
            self.assertApiValidationError(
                response,
                {
                    "publication_status": [
                        "Only a reviewer can change this project's status"
                    ]
                },
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
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_204_NO_CONTENT:
            for member in self.members:
                self.assertIn(member, project.members.all())
            for owner in self.owners:
                self.assertIn(owner, project.owners.all())
            for reviewer in self.reviewers:
                self.assertIn(reviewer, project.reviewers.all())
            for people_group in self.people_groups:
                self.assertIn(people_group, project.member_people_groups.all())

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
        # Create project with owner to avoid error when removing last owner
        project = ProjectFactory(organizations=[self.organization], with_owner=True)
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
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_204_NO_CONTENT:
            for member in self.members:
                self.assertNotIn(member, project.members.all())
            for owner in self.owners:
                self.assertNotIn(owner, project.owners.all())
            for reviewer in self.reviewers:
                self.assertNotIn(reviewer, project.reviewers.all())
            for people_group in self.people_groups:
                self.assertNotIn(people_group, project.member_people_groups.all())

    def test_remove_project_member_self(self):
        # Create project with owner to avoid error when removing last owner
        project = ProjectFactory(organizations=[self.organization], with_owner=True)
        to_delete = UserFactory()
        project.members.add(to_delete)
        self.client.force_authenticate(to_delete)
        response = self.client.delete(
            reverse("Project-remove-self", args=(project.id,))
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertNotIn(to_delete, project.members.all())


class DuplicateProjectTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.category = ProjectCategoryFactory(organization=cls.organization)
        cls.project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[cls.organization],
            categories=[cls.category],
            header_image=cls.get_test_image(),
        )
        blog_entries = BlogEntryFactory.create_batch(3, project=cls.project)
        GoalFactory.create_batch(3, project=cls.project)
        AttachmentLinkFactory.create_batch(3, project=cls.project)
        AttachmentFileFactory.create_batch(3, project=cls.project)
        AnnouncementFactory.create_batch(3, project=cls.project)
        tags = TagFactory.create_batch(3)
        cls.project.tags.set(tags)
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

    def check_duplicated_project(self, duplicated_project: Dict, initial_project: Dict):
        fields = [
            "is_locked",
            "title",
            "is_shareable",
            "purpose",
            "language",
            "life_status",
            "template",
        ]
        many_to_many_fields = [
            "categories",
            "tags",
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
        self.assertEqual(
            duplicated_project["publication_status"], Project.PublicationStatus.PRIVATE
        )
        for field in fields:
            self.assertEqual(duplicated_project[field], initial_project[field])

        for field in list_fields:
            self.assertSetEqual(
                set(duplicated_project[field]), set(initial_project[field])
            )

        for field in many_to_many_fields:
            self.assertSetEqual(
                {item["id"] for item in duplicated_project[field]},
                {item["id"] for item in initial_project[field]},
            )

        for related_field in related_fields:
            self.assertEqual(
                len(duplicated_project[related_field]),
                len(initial_project[related_field]),
            )
            duplicated_field = [
                {
                    key: value
                    for key, value in item.items()
                    if key not in ["id", "project", "created_at", "updated_at", "file"]
                }
                for item in duplicated_project[related_field]
            ]
            initial_field = [
                {
                    key: value
                    for key, value in item.items()
                    if key not in ["id", "project", "created_at", "updated_at", "file"]
                }
                for item in initial_project[related_field]
            ]
            self.assertEqual(len(duplicated_field), len(initial_field))
            for item in duplicated_field:
                self.assertIn(item, initial_field)

        self.assertEqual(
            len(duplicated_project["images"]), len(initial_project["images"])
        )
        for duplicated_image in duplicated_project["images"]:
            self.assertNotIn(
                duplicated_image["id"], [i["id"] for i in initial_project["images"]]
            )
            self.assertIn(
                f"<img src=\"/v1/project/{duplicated_project['id']}/image/{duplicated_image['id']}/\" />",
                duplicated_project["description"],
            )

        self.assertEqual(
            len(duplicated_project["blog_entries"]),
            len(initial_project["blog_entries"]),
        )
        for duplicated_blog_entry in duplicated_project["blog_entries"]:
            self.assertNotIn(
                duplicated_blog_entry["id"],
                [i["id"] for i in initial_project["blog_entries"]],
            )
        initial_blog_entry = list(
            filter(lambda x: len(x["images"]) > 0, initial_project["blog_entries"])
        )[0]
        duplicated_blog_entry = list(
            filter(lambda x: len(x["images"]) > 0, duplicated_project["blog_entries"])
        )[0]
        for duplicated_image in duplicated_blog_entry["images"]:
            self.assertNotIn(duplicated_image, initial_blog_entry["images"])
            self.assertIn(
                f"<img src=\"/v1/project/{duplicated_project['id']}/blog-entry-image/{duplicated_image}/\" />",
                duplicated_blog_entry["content"],
            )

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_201_CREATED),
            (TestRoles.ORG_ADMIN, status.HTTP_201_CREATED),
            (TestRoles.ORG_FACILITATOR, status.HTTP_201_CREATED),
            (TestRoles.ORG_USER, status.HTTP_201_CREATED),
            (TestRoles.PROJECT_MEMBER, status.HTTP_201_CREATED),
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
        cls.tag_1 = TagFactory()
        cls.tag_2 = TagFactory()
        cls.tag_3 = TagFactory()
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
        cls.project_1.tags.add(cls.tag_1, cls.tag_2)
        cls.project_2.tags.add(cls.tag_2, cls.tag_3)
        cls.project_3.tags.add(cls.tag_3)
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

    def setUp(self) -> None:
        super().setUp()
        self.client.force_authenticate(self.superadmin)

    def test_filter_by_category(self):
        response = self.client.get(
            reverse("Project-list")
            + f"?categories={self.category_1.id},{self.category_2.id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        content = response.json()
        self.assertEqual(content["count"], 2)
        self.assertEqual(
            {p["id"] for p in content["results"]},
            {self.project_1.id, self.project_2.id},
        )

    def test_filter_by_organization_code(self):
        response = self.client.get(
            reverse("Project-list") + f"?organizations={self.organization_1.code}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        content = response.json()
        self.assertEqual(content["count"], 2)
        self.assertEqual(
            {p["id"] for p in content["results"]},
            {self.project_1.id, self.project_3.id},
        )

    def test_filter_by_language(self):
        response = self.client.get(reverse("Project-list") + "?languages=en")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        content = response.json()
        self.assertEqual(content["count"], 2)
        self.assertEqual(
            {p["id"] for p in content["results"]},
            {self.project_2.id, self.project_3.id},
        )

    def test_filter_by_members(self):
        response = self.client.get(
            reverse("Project-list") + f"?members={self.user_2.id},{self.user_3.id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        content = response.json()
        self.assertEqual(content["count"], 2)
        self.assertEqual(
            {p["id"] for p in content["results"]},
            {self.project_2.id, self.project_3.id},
        )

    def test_filter_by_sdgs(self):
        response = self.client.get(reverse("Project-list") + "?sdgs=1,4,7")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        content = response.json()
        self.assertEqual(content["count"], 2)
        self.assertEqual(
            {p["id"] for p in content["results"]},
            {self.project_1.id, self.project_3.id},
        )

    def test_filter_by_tags(self):
        response = self.client.get(
            reverse("Project-list") + f"?tags={self.tag_1.id},{self.tag_2.id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        content = response.json()
        self.assertEqual(content["count"], 2)
        self.assertEqual(
            {p["id"] for p in content["results"]},
            {self.project_1.id, self.project_2.id},
        )

    def test_filter_by_member_role(self):
        response = self.client.get(
            reverse("Project-list")
            + f"?members={self.user_1.id},{self.user_2.id}"
            + f"&member_role={Project.DefaultGroup.OWNERS},{Project.DefaultGroup.MEMBERS}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["count"], 2)
        self.assertSetEqual(
            {p["id"] for p in response.data["results"]},
            {self.project_1.id, self.project_2.id},
        )

    def test_filter_by_life_status(self):
        response = self.client.get(
            reverse("Project-list")
            + f"?life_status={Project.LifeStatus.RUNNING},{Project.LifeStatus.COMPLETED}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(
            {p["id"] for p in response.data["results"]},
            {self.project_2.id, self.project_3.id},
        )

    def test_filter_by_creation_year(self):
        response = self.client.get(reverse("Project-list") + "?creation_year=2020,2021")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        content = response.json()
        self.assertEqual(content["count"], 2)
        self.assertEqual(
            {p["id"] for p in content["results"]},
            {self.project_1.id, self.project_2.id},
        )

    def test_filter_by_ids_and_slugs(self):
        response = self.client.get(
            reverse("Project-list") + f"?ids={self.project_1.id},{self.project_2.slug}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        content = response.json()
        self.assertEqual(content["count"], 2)
        self.assertEqual(
            {p["id"] for p in content["results"]},
            {self.project_1.id, self.project_2.id},
        )

    def test_order_by_created_date(self):
        response = self.client.get(reverse("Project-list") + "?ordering=created_at")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        content = response.json()
        self.assertEqual(content["count"], 3)
        self.assertLess(
            content["results"][0]["created_at"], content["results"][1]["created_at"]
        )
        self.assertLess(
            content["results"][1]["created_at"], content["results"][2]["created_at"]
        )

    def test_order_by_created_date_reverse(self):
        response = self.client.get(reverse("Project-list") + "?ordering=-created_at")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        content = response.json()
        self.assertEqual(content["count"], 3)
        self.assertGreater(
            content["results"][0]["created_at"], content["results"][1]["created_at"]
        )
        self.assertGreater(
            content["results"][1]["created_at"], content["results"][2]["created_at"]
        )

    def test_order_by_updated_date(self):
        response = self.client.get(reverse("Project-list") + "?ordering=updated_at")
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        content = response.json()
        self.assertEqual(content["count"], 3)
        self.assertLess(
            content["results"][0]["updated_at"], content["results"][1]["updated_at"]
        )
        self.assertLess(
            content["results"][1]["updated_at"], content["results"][2]["updated_at"]
        )

    def test_order_by_updated_date_reverse(self):
        response = self.client.get(reverse("Project-list") + "?ordering=-updated_at")
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
        cls.category = ProjectCategoryFactory(organization=cls.organization)
        cls.organization_2 = OrganizationFactory()
        cls.category_2 = ProjectCategoryFactory(organization=cls.organization_2)
        cls.superadmin = UserFactory(groups=[get_superadmins_group()])

    def test_update_without_organization(self):
        self.client.force_authenticate(self.superadmin)
        project = ProjectFactory(organizations=[self.organization])
        payload = {"organizations_codes": []}
        response = self.client.patch(
            reverse("Project-detail", args=(project.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertApiValidationError(
            response,
            {
                "organizations_codes": [
                    "A project must belong to at least one organization"
                ]
            },
        )

    def test_remove_last_member(self):
        self.client.force_authenticate(self.superadmin)
        project = ProjectFactory(organizations=[self.organization], with_owner=True)
        owner = project.owners.first()
        payload = {
            "users": [owner.id],
        }
        response = self.client.post(
            reverse("Project-remove-member", args=(project.id,)), data=payload
        )
        self.assertEqual(
            response.status_code, status.HTTP_400_BAD_REQUEST, response.content
        )
        self.assertApiValidationError(
            response, {"users": ["You cannot remove all the owners of a project"]}
        )

    def test_create_project_in_organization_with_no_rights(self):
        user = UserFactory(groups=[self.organization.get_users()])
        self.client.force_authenticate(user)
        payload = {
            "title": faker.sentence(),
            "organizations_codes": [self.organization.code, self.organization_2.code],
            "project_categories_ids": [self.category.id, self.category_2.id],
        }
        response = self.client.post(reverse("Project-list"), data=payload)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertApiPermissionError(
            response, "You do not have the rights to add a project in this organization"
        )

    def test_add_project_to_organization_with_no_rights(self):
        project = ProjectFactory(organizations=[self.organization])
        user = UserFactory(groups=[self.organization.get_users(), project.get_owners()])
        self.client.force_authenticate(user)
        payload = {
            "organizations_codes": [self.organization.code, self.organization_2.code],
        }
        response = self.client.patch(
            reverse("Project-detail", args=(project.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertApiPermissionError(
            response, "You do not have the rights to add a project in this organization"
        )

    def test_update_project_with_two_organizations(self):
        project = ProjectFactory(organizations=[self.organization, self.organization_2])
        user = UserFactory(groups=[self.organization.get_users(), project.get_owners()])
        self.client.force_authenticate(user)
        payload = {
            "title": faker.sentence(),
        }
        response = self.client.patch(
            reverse("Project-detail", args=(project.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["title"], payload["title"])


class MiscProjectTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.superadmin = UserFactory(groups=[get_superadmins_group()])

    def test_get_slug(self):
        title = "My AMazing TeST ProjeCT !"
        project = ProjectFactory(
            organizations=[self.organization],
            title=title,
            deleted_at=timezone.localtime(timezone.now()),
        )
        self.assertEqual(project.slug, "my-amazing-test-project")
        project = ProjectFactory(organizations=[self.organization], title=title)
        self.assertEqual(project.slug, "my-amazing-test-project-1")
        project = ProjectFactory(organizations=[self.organization], title=title)
        self.assertEqual(project.slug, "my-amazing-test-project-2")

    def test_blank_raw_slug(self):
        title = "."
        project = ProjectFactory(
            organizations=[self.organization],
            title=title,
            deleted_at=timezone.localtime(timezone.now()),
        )
        self.assertEqual(project.slug, "project-0")

    def test_change_member_role(self):
        self.client.force_authenticate(self.superadmin)
        project = ProjectFactory(organizations=[self.organization])
        user = UserFactory(groups=[project.get_members()])
        payload = {
            Project.DefaultGroup.OWNERS: [user.id],
        }
        response = self.client.post(
            reverse("Project-add-member", args=(project.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertIn(user, project.owners.all())
        self.assertNotIn(user, project.members.all())

    def test_is_followed_get(self):
        project = ProjectFactory(organizations=[self.organization])
        user = self.superadmin
        self.client.force_authenticate(user)

        response = self.client.get(reverse("Project-detail", args=(project.id,)))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.json()["is_followed"]["is_followed"])

        follow = FollowFactory(follower=user, project=project)
        response = self.client.get(reverse("Project-detail", args=(project.id,)))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertTrue(content["is_followed"]["is_followed"])
        self.assertEqual(content["is_followed"]["follow_id"], follow.id)

    def test_is_followed_list(self):
        projects = ProjectFactory.create_batch(3, organizations=[self.organization])
        user = self.superadmin
        follow_1 = FollowFactory(follower=user, project=projects[0])
        follow_2 = FollowFactory(follower=user, project=projects[1])
        self.client.force_authenticate(user)

        response = self.client.get(reverse("Project-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertSetEqual(
            {projects[0].id, projects[1].id},
            {
                p["id"]
                for p in list(
                    filter(lambda x: x["is_followed"]["is_followed"], content)
                )
            },
        )
        self.assertSetEqual(
            {follow_1.id, follow_2.id},
            {
                p["is_followed"]["follow_id"]
                for p in list(
                    filter(lambda x: x["is_followed"]["is_followed"], content)
                )
            },
        )

    def test_add_reviewer_to_public_project(self):
        self.client.force_authenticate(self.superadmin)
        project = ProjectFactory(
            organizations=[self.organization],
            categories=[ProjectCategoryFactory(only_reviewer_can_publish=True)],
        )
        reviewer = UserFactory()
        payload = {
            Project.DefaultGroup.REVIEWERS: [reviewer.id],
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
            Project.DefaultGroup.REVIEWERS: [reviewer.id],
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
