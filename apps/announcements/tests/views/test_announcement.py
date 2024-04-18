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


class ReadAnnouncementTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        projects = {
            "public": ProjectFactory(
                organizations=[cls.organization],
                publication_status=Project.PublicationStatus.PUBLIC,
            ),
            "org": ProjectFactory(
                organizations=[cls.organization],
                publication_status=Project.PublicationStatus.ORG,
            ),
            "private": ProjectFactory(
                organizations=[cls.organization],
                publication_status=Project.PublicationStatus.PRIVATE,
            ),
        }
        cls.announcements = {
            "public": AnnouncementFactory(project=projects["public"]),
            "org": AnnouncementFactory(project=projects["org"]),
            "private": AnnouncementFactory(project=projects["private"]),
        }

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, "public"),
            (TestRoles.ANONYMOUS, "org"),
            (TestRoles.ANONYMOUS, "private"),
            (TestRoles.DEFAULT, "public"),
            (TestRoles.DEFAULT, "org"),
            (TestRoles.DEFAULT, "private"),
        ]
    )
    def test_retrieve_announcement(self, role, publication_status):
        user = self.get_parameterized_test_user(role)
        announcement = self.announcements[publication_status]
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("Read-announcement-detail", args=(announcement.id,)),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["id"], announcement.id)

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS,),
            (TestRoles.DEFAULT,),
        ]
    )
    def test_list_announcement(self, role):
        user = self.get_parameterized_test_user(role)
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("Read-announcement-list"),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), len(self.announcements))
        self.assertSetEqual(
            {a["id"] for a in content},
            {a.id for a in self.announcements.values()},
        )


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
