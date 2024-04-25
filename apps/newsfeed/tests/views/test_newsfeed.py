import datetime
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from django.utils.timezone import make_aware
from parameterized import parameterized
from rest_framework import status

from apps.accounts.factories import PeopleGroupFactory
from apps.accounts.models import PeopleGroup
from apps.announcements.factories import AnnouncementFactory
from apps.announcements.models import Announcement
from apps.commons.test import JwtAPITestCase, TestRoles
from apps.newsfeed.factories import NewsFactory
from apps.newsfeed.models import News, Newsfeed
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory, ProjectScoreFactory
from apps.projects.models import Project


class NewsfeedTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        Project.objects.all().delete()  # Delete projects created by the factories
        Announcement.objects.all().delete()  # Delete announcements created by the factories
        News.objects.all().delete()  # Delete news created by the factories
        Newsfeed.objects.all().delete()  # Delete newsfeeds created by the factories

        cls.member_project = ProjectFactory(
            publication_status=Project.PublicationStatus.PRIVATE,
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
        cls.public_project_not_complete = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[cls.organization],
        )
        cls.public_project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[cls.organization],
        )

        ProjectScoreFactory(project=cls.member_project, completeness=9.0)
        ProjectScoreFactory(project=cls.org_project, completeness=8.0)
        ProjectScoreFactory(project=cls.private_project, completeness=7.0)
        ProjectScoreFactory(project=cls.public_project_not_complete, completeness=4.0)
        ProjectScoreFactory(project=cls.public_project, completeness=6.0)

        cls.date_1 = make_aware(datetime.datetime(2020, 1, 1))
        cls.date_2 = make_aware(datetime.datetime(2020, 2, 1))
        cls.date_3 = make_aware(datetime.datetime(2020, 3, 1))
        cls.date_4 = make_aware(datetime.datetime(2020, 4, 1))

        cls.projects = {
            "public": cls.public_project,
            "public_not_complete": cls.public_project_not_complete,
            "private": cls.private_project,
            "org": cls.org_project,
            "member": cls.member_project,
        }

        cls.projects_id = [project.id for project in cls.projects.values()][::-1]
        cls.projects_status = {
            project.id: status for status, project in cls.projects.items()
        }

        cls.member_announcement = AnnouncementFactory(project=cls.projects["member"])
        cls.org_announcement = AnnouncementFactory(project=cls.projects["org"])
        cls.private_announcement = AnnouncementFactory(project=cls.projects["private"])
        cls.public_not_complete_announcement = AnnouncementFactory(
            project=cls.projects["public_not_complete"]
        )
        cls.public_announcement = AnnouncementFactory(project=cls.projects["public"])

        cls.announcements = {
            "public": cls.public_announcement,
            "public_not_complete": cls.public_not_complete_announcement,
            "private": cls.private_announcement,
            "org": cls.org_announcement,
            "member": cls.member_announcement,
        }
        cls.announcements_id = [
            cls.announcements[announcement].id for announcement in cls.announcements
        ].reverse()
        cls.announcements_status = {
            announcement.id: status
            for status, announcement in cls.announcements.items()
        }

        cls.news_data = {
            "all": [None, True, cls.date_4],
            "none": [None, False, cls.date_4],
            "public": [
                [
                    PeopleGroupFactory(
                        organization=cls.organization,
                        publication_status=PeopleGroup.PublicationStatus.PUBLIC,
                    )
                ],
                False,
                cls.date_3,
            ],
            "private": [
                [
                    PeopleGroupFactory(
                        organization=cls.organization,
                        publication_status=PeopleGroup.PublicationStatus.PRIVATE,
                    )
                ],
                False,
                cls.date_2,
            ],
            "org": [
                [
                    PeopleGroupFactory(
                        organization=cls.organization,
                        publication_status=PeopleGroup.PublicationStatus.ORG,
                    )
                ],
                False,
                cls.date_1,
            ],
        }

        cls.news = {
            key: NewsFactory(
                organization=cls.organization,
                people_groups=value[0],
                visible_by_all=value[1],
                publication_date=value[2],
            )
            for key, value in cls.news_data.items()
        }
        cls.news["public_in_future"] = NewsFactory(
            organization=cls.organization,
            people_groups=None,
            visible_by_all=True,
            publication_date=timezone.now() + timedelta(days=1),
        )
        cls.news_status = {news.id: status for status, news in cls.news.items()}

        cls.newsfeed_projects_ids = {
            newsfeed.project.id: newsfeed
            for newsfeed in Newsfeed.objects.all()
            if newsfeed.type == Newsfeed.NewsfeedType.PROJECT
        }
        cls.newsfeed_announcements_ids = {
            newsfeed.announcement.id: newsfeed
            for newsfeed in Newsfeed.objects.all()
            if newsfeed.type == Newsfeed.NewsfeedType.ANNOUNCEMENT
        }

        cls.newsfeed_news_ids = {
            newsfeed.news.id: newsfeed
            for newsfeed in Newsfeed.objects.all()
            if newsfeed.type == Newsfeed.NewsfeedType.NEWS
        }

    @parameterized.expand(
        [
            (
                TestRoles.ANONYMOUS,
                [
                    ("public", "public_not_complete", "private", "org", "member"),
                    ("all", "public"),
                    ("public",),
                ],
            ),
            (
                TestRoles.DEFAULT,
                [
                    ("public", "public_not_complete", "private", "org", "member"),
                    ("all", "public"),
                    ("public",),
                ],
            ),
            (
                TestRoles.SUPERADMIN,
                [
                    ("public", "public_not_complete", "private", "org", "member"),
                    ("all", "none", "public", "private", "org"),
                    ("public", "private", "org", "member"),
                ],
            ),
            (
                TestRoles.ORG_ADMIN,
                [
                    ("public", "public_not_complete", "private", "org", "member"),
                    ("all", "public", "private", "org"),
                    ("public", "private", "org", "member"),
                ],
            ),
            (
                TestRoles.ORG_FACILITATOR,
                [
                    ("public", "public_not_complete", "private", "org", "member"),
                    ("all", "public", "private", "org"),
                    ("public", "private", "org", "member"),
                ],
            ),
            (
                TestRoles.ORG_USER,
                [
                    ("public", "public_not_complete", "private", "org", "member"),
                    ("all", "public", "org"),
                    ("public", "org"),
                ],
            ),
            (
                TestRoles.PROJECT_MEMBER,
                [
                    ("public", "public_not_complete", "private", "org", "member"),
                    ("all", "public"),
                    ("public", "member"),
                ],
            ),
        ]
    )
    def test_list_projects(self, role, retrieved_newsfeed):
        # Retrieved_newsfeed is a list, whose first element is applicable to announcements, whose second element is applicable to news and whose last element is applicable to projects.
        user = self.get_parameterized_test_user(role, instances=[self.member_project])
        self.client.force_authenticate(user)

        response = self.client.get(
            reverse("Newsfeed-list", args=(self.organization.code,))
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        content = response.json()["results"]

        retrieved_announcements = [
            self.announcements[status].id for status in retrieved_newsfeed[0]
        ]
        retrieved_news = [self.news[status].id for status in retrieved_newsfeed[1]]
        retrieved_projects = [
            self.projects[status].id for status in retrieved_newsfeed[2]
        ]

        expected_ordered_list = []
        max_length = max(
            len(retrieved_announcements), len(retrieved_news), len(retrieved_projects)
        )

        for x in range(max_length):
            if x < len(retrieved_announcements):
                expected_ordered_list.append(
                    {
                        "newsfeed": self.newsfeed_announcements_ids[
                            retrieved_announcements[x]
                        ],
                        "type": "announcement",
                    }
                )
            if x < len(retrieved_news):
                expected_ordered_list.append(
                    {
                        "newsfeed": self.newsfeed_news_ids[retrieved_news[x]],
                        "type": "news",
                    }
                )
            if x < len(retrieved_projects):
                expected_ordered_list.append(
                    {
                        "newsfeed": self.newsfeed_projects_ids[retrieved_projects[x]],
                        "type": "project",
                    }
                )
            x += 1

        for i in range(len(content)):
            self.assertEqual(content[i]["id"], expected_ordered_list[i]["newsfeed"].id)
            self.assertEqual(content[i]["type"], expected_ordered_list[i]["type"])
