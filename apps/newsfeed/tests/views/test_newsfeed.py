import datetime

from django.urls import reverse
from django.utils.timezone import make_aware
from parameterized import parameterized
from rest_framework import status

from apps.announcements.factories import AnnouncementFactory
from apps.announcements.models import Announcement
from apps.commons.test import JwtAPITestCase, TestRoles
from apps.newsfeed.models import Newsfeed
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory
from apps.projects.models import Project


class NewsfeedTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        Project.objects.all().delete()  # Delete projects created by the factories
        Announcement.objects.all().delete()  # Delete announcements created by the factories
        Newsfeed.objects.all().delete()  # Delete newsfeeds created by the factories

        cls.public_project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[cls.organization],
        )
        cls.private_project = ProjectFactory(
            publication_status=Project.PublicationStatus.PRIVATE,
            organizations=[cls.organization],
        )
        cls.org_project = ProjectFactory(
            publication_status=Project.PublicationStatus.ORG,
            organizations=[cls.organization],
        )
        cls.member_project = ProjectFactory(
            publication_status=Project.PublicationStatus.PRIVATE,
            organizations=[cls.organization],
        )

        cls.date_1 = make_aware(datetime.datetime(2020, 1, 1))
        cls.date_2 = make_aware(datetime.datetime(2020, 2, 1))
        cls.date_3 = make_aware(datetime.datetime(2020, 3, 1))
        cls.date_4 = make_aware(datetime.datetime(2020, 4, 1))

        Project.objects.filter(pk=cls.public_project.pk).update(
            created_at=cls.date_1, updated_at=cls.date_1
        )
        Project.objects.filter(pk=cls.private_project.pk).update(
            created_at=cls.date_1, updated_at=cls.date_2
        )
        Project.objects.filter(pk=cls.org_project.pk).update(
            created_at=cls.date_2, updated_at=cls.date_3
        )
        Project.objects.filter(pk=cls.member_project.pk).update(
            created_at=cls.date_3, updated_at=cls.date_4
        )

        cls.projects = {
            "public": cls.public_project,
            "private": cls.private_project,
            "org": cls.org_project,
            "member": cls.member_project,
        }

        cls.projects_id = [project.id for project in cls.projects.values()][::-1]
        cls.projects_status = {
            project.id: status for status, project in cls.projects.items()
        }

        cls.public_announcement = AnnouncementFactory(project=cls.projects["public"])
        cls.org_announcement = AnnouncementFactory(project=cls.projects["org"])
        cls.private_announcement = AnnouncementFactory(project=cls.projects["private"])
        cls.member_announcement = AnnouncementFactory(project=cls.projects["member"])

        Announcement.objects.filter(pk=cls.public_announcement.pk).update(
            created_at=cls.date_1, updated_at=cls.date_1
        )
        Announcement.objects.filter(pk=cls.private_announcement.pk).update(
            created_at=cls.date_1, updated_at=cls.date_2
        )
        Announcement.objects.filter(pk=cls.org_announcement.pk).update(
            created_at=cls.date_2, updated_at=cls.date_3
        )
        Announcement.objects.filter(pk=cls.member_announcement.pk).update(
            created_at=cls.date_3, updated_at=cls.date_4
        )

        cls.announcements = {
            "public": cls.public_announcement,
            "org": cls.org_announcement,
            "private": cls.private_announcement,
            "member": cls.member_announcement,
        }

        cls.announcements_id = [
            cls.announcements[announcement].id for announcement in cls.announcements
        ].reverse()

        cls.newsfeed_projects_ids = {
            cls.projects_status[newsfeed.project.id]: newsfeed.id
            for newsfeed in Newsfeed.objects.all()
            if newsfeed.type == Newsfeed.NewsfeedType.PROJECT
        }
        cls.newsfeed_announcements_ids = [
            newsfeed.id
            for newsfeed in Newsfeed.objects.all()
            if newsfeed.type == Newsfeed.NewsfeedType.ANNOUNCEMENT
        ]

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, ("public",)),
            (TestRoles.DEFAULT, ("public",)),
            (TestRoles.SUPERADMIN, ("public", "private", "org", "member")),
            (TestRoles.ORG_ADMIN, ("public", "private", "org", "member")),
            (TestRoles.ORG_FACILITATOR, ("public", "private", "org", "member")),
            (TestRoles.ORG_USER, ("public", "org")),
            (TestRoles.PROJECT_MEMBER, ("public", "member")),
            (TestRoles.PROJECT_OWNER, ("public", "member")),
            (TestRoles.PROJECT_REVIEWER, ("public", "member")),
        ]
    )
    def test_list_projects(self, role, retrieved_newsfeed):
        user = self.get_parameterized_test_user(role, instances=[self.member_project])
        self.client.force_authenticate(user)

        index = {
            1: {"projects": [0], "announcements": [1, 2, 3, 4]},
            2: {"projects": [0, 1], "announcements": [2, 3, 4, 5]},
            3: {"projects": [0, 1, 2], "announcements": [3, 4, 5, 6]},
            4: {"projects": [0, 1, 2, 5], "announcements": [3, 4, 6, 7]},
        }

        response = self.client.get(
            reverse("Newsfeed-list", args=(self.organization.code,))
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        content = response.json()["results"]
        self.assertEqual(len(content), len(retrieved_newsfeed) + 4)

        length = len(retrieved_newsfeed)
        projects_index = index[length]["projects"]
        announcements_index = index[length]["announcements"]
        previous_date = None
        retrieved_projects = [self.projects[status].id for status in retrieved_newsfeed]
        retrieved_announcements = [
            announcement.id for announcement in self.announcements.values()
        ]

        for i in range(length):
            result_proj_index = projects_index[i]
            self.assertEqual(content[result_proj_index]["type"], "project")
            self.assertIn(
                content[result_proj_index]["project"]["id"], retrieved_projects
            )
            if previous_date:
                self.assertTrue(
                    previous_date > content[result_proj_index]["project"]["updated_at"]
                )
            previous_date = content[result_proj_index]["project"]["updated_at"]
            i += 1

        previous_date = None
        for i in range(len(announcements_index)):
            result_ann_index = announcements_index[i]
            self.assertEqual(content[result_ann_index]["type"], "announcement")
            self.assertIn(
                content[result_ann_index]["announcement"]["id"], retrieved_announcements
            )
            if previous_date:
                self.assertTrue(
                    previous_date
                    > content[result_ann_index]["announcement"]["updated_at"]
                )
            previous_date = content[result_ann_index]["announcement"]["updated_at"]
            i += 1
