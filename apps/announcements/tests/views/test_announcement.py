import datetime

from django.urls import reverse
from django.utils.timezone import make_aware
from faker import Faker
from parameterized import parameterized
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.accounts.utils import get_superadmins_group
from apps.announcements.factories import AnnouncementFactory
from apps.announcements.models import Announcement
from apps.commons.test import JwtAPITestCase, TestRoles
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory
from apps.projects.models import Project

faker = Faker()


class CreateAnnouncementTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.project = ProjectFactory(organizations=[cls.organization])

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
    def test_create_announcement(self, role, expected_status_code):
        user = self.get_parameterized_test_user(role, instances=[self.project])
        self.client.force_authenticate(user)
        payload = {
            "title": faker.sentence(),
            "description": faker.text(),
            "type": Announcement.AnnouncementType.JOB,
            "is_remunerated": faker.boolean(),
            "project_id": self.project.id,
        }
        response = self.client.post(
            reverse("Announcement-list", args=(self.project.id,)),
            data=payload,
        )
        self.assertEqual(response.status_code, expected_status_code)
        if expected_status_code == status.HTTP_201_CREATED:
            content = response.json()
            self.assertEqual(content["title"], payload["title"])
            self.assertEqual(content["description"], payload["description"])
            self.assertEqual(content["type"], payload["type"])
            self.assertEqual(content["is_remunerated"], payload["is_remunerated"])
            self.assertEqual(content["project"]["id"], payload["project_id"])


class UpdateAnnouncementTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.project = ProjectFactory(organizations=[cls.organization])
        cls.announcement = AnnouncementFactory(project=cls.project)

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
    def test_update_announcement(self, role, expected_status_code):
        user = self.get_parameterized_test_user(role, instances=[self.project])
        self.client.force_authenticate(user)
        payload = {"description": faker.text()}
        response = self.client.patch(
            reverse(
                "Announcement-detail",
                args=(self.project.id, self.announcement.id),
            ),
            data=payload,
        )
        self.assertEqual(response.status_code, expected_status_code)
        if expected_status_code == status.HTTP_200_OK:
            content = response.json()
            self.assertEqual(content["description"], payload["description"])


class DeleteAnnouncementTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.project = ProjectFactory(organizations=[cls.organization])

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
    def test_delete_announcement(self, role, expected_status_code):
        announcement = AnnouncementFactory(project=self.project)
        user = self.get_parameterized_test_user(role, instances=[self.project])
        self.client.force_authenticate(user)
        response = self.client.delete(
            reverse(
                "Announcement-detail",
                args=(self.project.id, announcement.id),
            ),
        )
        self.assertEqual(response.status_code, expected_status_code)
        if expected_status_code == status.HTTP_204_NO_CONTENT:
            self.assertFalse(Announcement.objects.filter(id=announcement.id).exists())


class ReadAndApplyToAnnouncementTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.public_project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[cls.organization],
        )
        cls.org_project = ProjectFactory(
            publication_status=Project.PublicationStatus.ORG,
            organizations=[cls.organization],
        )
        cls.private_project = ProjectFactory(
            publication_status=Project.PublicationStatus.PRIVATE,
            organizations=[cls.organization],
        )
        cls.projects = {
            "public": cls.public_project,
            "org": cls.org_project,
            "private": cls.private_project,
        }
        cls.public_announcement = AnnouncementFactory(project=cls.public_project)
        cls.org_announcement = AnnouncementFactory(project=cls.org_project)
        cls.private_announcement = AnnouncementFactory(project=cls.private_project)
        cls.announcements = {
            "public": cls.public_announcement,
            "org": cls.org_announcement,
            "private": cls.private_announcement,
        }

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, ("public",)),
            (TestRoles.DEFAULT, ("public",)),
            (TestRoles.SUPERADMIN, ("public", "org", "private")),
            (TestRoles.ORG_ADMIN, ("public", "org", "private")),
            (TestRoles.ORG_FACILITATOR, ("public", "org", "private")),
            (TestRoles.ORG_USER, ("public", "org")),
            (TestRoles.PROJECT_MEMBER, ("public", "org", "private")),
            (TestRoles.PROJECT_OWNER, ("public", "org", "private")),
            (TestRoles.PROJECT_REVIEWER, ("public", "org", "private")),
        ]
    )
    def test_list_announcements(self, role, retrieved_announcements):
        for visibility, announcement in self.announcements.items():
            user = self.get_parameterized_test_user(
                role, instances=list(self.projects.values())
            )
            self.client.force_authenticate(user)
            response = self.client.get(
                reverse("Announcement-list", args=(announcement.project.id,))
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            content = response.json()["results"]
            if visibility in retrieved_announcements:
                self.assertEqual(len(content), 1)
                self.assertEqual(content[0]["id"], announcement.id)
            else:
                self.assertEqual(len(content), 0)

        user = self.get_parameterized_test_user(
            role, instances=list(self.projects.values())
        )
        self.client.force_authenticate(user)
        read_response = self.client.get(reverse("Read-announcement-list"))
        self.assertEqual(read_response.status_code, status.HTTP_200_OK)
        content = read_response.json()["results"]
        self.assertEqual(len(content), len(retrieved_announcements))
        self.assertSetEqual(
            {a["id"] for a in content},
            {
                self.announcements[project_status].id
                for project_status in retrieved_announcements
            },
        )

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, ("public",)),
            (TestRoles.DEFAULT, ("public",)),
            (TestRoles.SUPERADMIN, ("public", "org", "private")),
            (TestRoles.ORG_ADMIN, ("public", "org", "private")),
            (TestRoles.ORG_FACILITATOR, ("public", "org", "private")),
            (TestRoles.ORG_USER, ("public", "org")),
            (TestRoles.PROJECT_MEMBER, ("public", "org", "private")),
            (TestRoles.PROJECT_OWNER, ("public", "org", "private")),
            (TestRoles.PROJECT_REVIEWER, ("public", "org", "private")),
        ]
    )
    def test_retrieve_announcements(self, role, retrieved_announcements):
        for visibility, announcement in self.announcements.items():
            user = self.get_parameterized_test_user(
                role, instances=list(self.projects.values())
            )
            self.client.force_authenticate(user)
            response = self.client.get(
                reverse(
                    "Announcement-detail",
                    args=(announcement.project.id, announcement.id),
                )
            )
            if visibility in retrieved_announcements:
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                content = response.json()
                self.assertEqual(content["id"], announcement.id)
            else:
                self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        user = self.get_parameterized_test_user(
            role, instances=list(self.projects.values())
        )
        self.client.force_authenticate(user)
        read_response = self.client.get(
            reverse("Read-announcement-detail", args=(announcement.id,))
        )
        if visibility in retrieved_announcements:
            self.assertEqual(read_response.status_code, status.HTTP_200_OK)
            content = read_response.json()
            self.assertEqual(content["id"], announcement.id)
        else:
            self.assertEqual(read_response.status_code, status.HTTP_404_NOT_FOUND)

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, ("public",)),
            (TestRoles.DEFAULT, ("public",)),
            (TestRoles.SUPERADMIN, ("public", "org", "private")),
            (TestRoles.ORG_ADMIN, ("public", "org", "private")),
            (TestRoles.ORG_FACILITATOR, ("public", "org", "private")),
            (TestRoles.ORG_USER, ("public", "org")),
            (TestRoles.PROJECT_MEMBER, ("public", "org", "private")),
            (TestRoles.PROJECT_OWNER, ("public", "org", "private")),
            (TestRoles.PROJECT_REVIEWER, ("public", "org", "private")),
        ]
    )
    def test_apply_to_announcement(self, role, visible_announcements):
        user = self.get_parameterized_test_user(
            role, instances=list(self.projects.values())
        )
        self.client.force_authenticate(user)
        for visibility, announcement in self.announcements.items():
            payload = {
                "project_id": announcement.project.id,
                "announcement_id": announcement.id,
                "applicant_name": faker.last_name(),
                "applicant_firstname": faker.first_name(),
                "applicant_email": faker.email(),
                "applicant_message": faker.text(),
                "recaptcha": faker.word(),
            }
            response = self.client.post(
                reverse(
                    "Announcement-apply",
                    args=(announcement.project.id, announcement.id),
                ),
                data=payload,
            )
            if visibility in visible_announcements:
                self.assertEqual(response.status_code, status.HTTP_200_OK)
            else:
                self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class FilterOrderAnnouncementTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.project = ProjectFactory(organizations=[cls.organization])
        cls.user = UserFactory(groups=[get_superadmins_group()])
        cls.date_1 = make_aware(datetime.datetime(2020, 1, 1))
        cls.date_2 = make_aware(datetime.datetime(2021, 1, 1))
        cls.date_3 = make_aware(datetime.datetime(2022, 1, 1))
        cls.announcement_1 = AnnouncementFactory(
            project=cls.project, deadline=cls.date_1
        )
        cls.announcement_2 = AnnouncementFactory(
            project=cls.project, deadline=cls.date_2
        )
        cls.announcement_3 = AnnouncementFactory(
            project=cls.project, deadline=cls.date_3
        )
        cls.announcement_4 = AnnouncementFactory(project=cls.project, deadline=None)

    def test_filter_from_date(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(
            reverse("Announcement-list", args=(self.project.id,))
            + f"?from_date={self.date_2.date()}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertSetEqual(
            {a["id"] for a in content},
            {self.announcement_2.id, self.announcement_3.id},
        )

    def test_filter_to_date(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(
            reverse("Announcement-list", args=(self.project.id,))
            + f"?to_date={self.date_2.date()}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertSetEqual(
            {a["id"] for a in content},
            {self.announcement_1.id, self.announcement_2.id},
        )

    def test_filter_from_date_with_null(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(
            reverse("Announcement-list", args=(self.project.id,))
            + f"?from_date_or_none={self.date_2.date()}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertSetEqual(
            {a["id"] for a in content},
            {self.announcement_2.id, self.announcement_3.id, self.announcement_4.id},
        )

    def test_filter_to_date_with_null(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(
            reverse("Announcement-list", args=(self.project.id,))
            + f"?to_date_or_none={self.date_2.date()}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertSetEqual(
            {a["id"] for a in content},
            {self.announcement_1.id, self.announcement_2.id, self.announcement_4.id},
        )

    def test_order_by_deadline(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(
            reverse("Announcement-list", args=(self.project.id,)) + "?ordering=deadline"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertListEqual(
            [a["id"] for a in content],
            [
                self.announcement_1.id,
                self.announcement_2.id,
                self.announcement_3.id,
                self.announcement_4.id,
            ],
        )

    def test_order_by_deadline_reverse(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(
            reverse("Announcement-list", args=(self.project.id,))
            + "?ordering=-deadline"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertListEqual(
            [a["id"] for a in content],
            [
                self.announcement_4.id,
                self.announcement_3.id,
                self.announcement_2.id,
                self.announcement_1.id,
            ],
        )
