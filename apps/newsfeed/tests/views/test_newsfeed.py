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
from apps.commons.test import JwtAPITestCase, TestRoles
from apps.newsfeed.factories import NewsFactory
from apps.newsfeed.models import Newsfeed
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory, ProjectScoreFactory
from apps.projects.models import Project


class NewsfeedTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.date_1 = make_aware(datetime.datetime(2020, 1, 1))
        cls.date_2 = make_aware(datetime.datetime(2020, 2, 1))
        cls.date_3 = make_aware(datetime.datetime(2020, 3, 1))
        cls.date_4 = make_aware(datetime.datetime(2020, 4, 1))
        cls.date_5 = make_aware(datetime.datetime(2020, 5, 1))

        cls.organization = OrganizationFactory()

        cls.member_project = ProjectFactory(
            publication_status=Project.PublicationStatus.PRIVATE,
            organizations=[cls.organization],
            updated_at=cls.date_1,
        )
        cls.org_project = ProjectFactory(
            publication_status=Project.PublicationStatus.ORG,
            organizations=[cls.organization],
            updated_at=cls.date_2,
        )
        cls.private_project = ProjectFactory(
            publication_status=Project.PublicationStatus.PRIVATE,
            organizations=[cls.organization],
            updated_at=cls.date_3,
        )
        cls.public_project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[cls.organization],
            updated_at=cls.date_4,
        )
        cls.public_project_not_complete = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[cls.organization],
            updated_at=cls.date_5,
        )
        ProjectScoreFactory(project=cls.member_project, completeness=5.0)
        ProjectScoreFactory(project=cls.org_project, completeness=5.0)
        ProjectScoreFactory(project=cls.private_project, completeness=5.0)
        ProjectScoreFactory(project=cls.public_project, completeness=5.0)
        ProjectScoreFactory(project=cls.public_project_not_complete, completeness=4.0)

        cls.member_announcement = AnnouncementFactory(
            project=cls.member_project,
            updated_at=cls.date_1,
        )
        cls.org_announcement = AnnouncementFactory(
            project=cls.org_project,
            updated_at=cls.date_2,
        )
        cls.private_announcement = AnnouncementFactory(
            project=cls.private_project,
            updated_at=cls.date_3,
        )
        cls.public_announcement = AnnouncementFactory(
            project=cls.public_project,
            updated_at=cls.date_4,
        )
        cls.public_not_complete_announcement = AnnouncementFactory(
            project=cls.public_project_not_complete,
            updated_at=cls.date_5,
        )
        cls.expired_announcement = AnnouncementFactory(
            project=cls.public_project,
            updated_at=cls.date_1 - timedelta(days=1),
            deadline=timezone.now() - timedelta(days=1),
        )

        cls.public_people_group = PeopleGroupFactory(
            organization=cls.organization,
            publication_status=PeopleGroup.PublicationStatus.PUBLIC,
        )
        cls.private_people_group = PeopleGroupFactory(
            organization=cls.organization,
            publication_status=PeopleGroup.PublicationStatus.PRIVATE,
        )
        cls.org_people_group = PeopleGroupFactory(
            organization=cls.organization,
            publication_status=PeopleGroup.PublicationStatus.ORG,
        )

        cls.all_news = NewsFactory(
            organization=cls.organization,
            people_groups=None,
            visible_by_all=True,
            publication_date=cls.date_1,
        )
        cls.public_news = NewsFactory(
            organization=cls.organization,
            people_groups=[cls.public_people_group],
            visible_by_all=False,
            publication_date=cls.date_2,
        )
        cls.private_news = NewsFactory(
            organization=cls.organization,
            people_groups=[cls.private_people_group],
            visible_by_all=False,
            publication_date=cls.date_3,
        )
        cls.org_news = NewsFactory(
            organization=cls.organization,
            people_groups=[cls.org_people_group],
            visible_by_all=False,
            publication_date=cls.date_4,
        )
        cls.public_in_future_news = NewsFactory(
            organization=cls.organization,
            people_groups=None,
            visible_by_all=True,
            publication_date=timezone.now() + timedelta(days=1),
        )
        cls.newsfeed = {
            # announcements
            "public_not_complete_announcement": Newsfeed.objects.get(
                announcement=cls.public_not_complete_announcement
            ),
            "public_announcement": Newsfeed.objects.get(
                announcement=cls.public_announcement
            ),
            "private_announcement": Newsfeed.objects.get(
                announcement=cls.private_announcement
            ),
            "org_announcement": Newsfeed.objects.get(announcement=cls.org_announcement),
            "member_announcement": Newsfeed.objects.get(
                announcement=cls.member_announcement
            ),
            # news
            "org_news": Newsfeed.objects.get(news=cls.org_news),
            "private_news": Newsfeed.objects.get(news=cls.private_news),
            "public_news": Newsfeed.objects.get(news=cls.public_news),
            "all_news": Newsfeed.objects.get(news=cls.all_news),
            # projects
            "public_project": Newsfeed.objects.get(project=cls.public_project),
            "private_project": Newsfeed.objects.get(project=cls.private_project),
            "org_project": Newsfeed.objects.get(project=cls.org_project),
            "member_project": Newsfeed.objects.get(project=cls.member_project),
        }

    @parameterized.expand(
        [
            (
                TestRoles.ANONYMOUS,
                [
                    "public_not_complete_announcement",
                    "public_news",
                    "public_project",
                    "public_announcement",
                    "all_news",
                ],
            ),
            (
                TestRoles.DEFAULT,
                [
                    "public_not_complete_announcement",
                    "public_news",
                    "public_project",
                    "public_announcement",
                    "all_news",
                ],
            ),
            (
                TestRoles.SUPERADMIN,
                [
                    "public_not_complete_announcement",
                    "org_news",
                    "public_project",
                    "public_announcement",
                    "private_news",
                    "private_project",
                    "private_announcement",
                    "public_news",
                    "org_project",
                    "org_announcement",
                    "all_news",
                    "member_project",
                    "member_announcement",
                ],
            ),
            (
                TestRoles.ORG_ADMIN,
                [
                    "public_not_complete_announcement",
                    "org_news",
                    "public_project",
                    "public_announcement",
                    "private_news",
                    "private_project",
                    "private_announcement",
                    "public_news",
                    "org_project",
                    "org_announcement",
                    "all_news",
                    "member_project",
                    "member_announcement",
                ],
            ),
            (
                TestRoles.ORG_FACILITATOR,
                [
                    "public_not_complete_announcement",
                    "org_news",
                    "public_project",
                    "public_announcement",
                    "private_news",
                    "private_project",
                    "private_announcement",
                    "public_news",
                    "org_project",
                    "org_announcement",
                    "all_news",
                    "member_project",
                    "member_announcement",
                ],
            ),
            (
                TestRoles.ORG_USER,
                [
                    "public_not_complete_announcement",
                    "org_news",
                    "public_project",
                    "public_announcement",
                    "public_news",
                    "org_project",
                    "org_announcement",
                    "all_news",
                ],
            ),
            (
                TestRoles.PROJECT_MEMBER,
                [
                    "public_not_complete_announcement",
                    "public_news",
                    "public_project",
                    "public_announcement",
                    "all_news",
                    "member_project",
                    "member_announcement",
                ],
            ),
        ]
    )
    def test_list_projects(self, role, retrieved_newsfeed):
        user = self.get_parameterized_test_user(role, instances=[self.member_project])
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("Newsfeed-list", args=(self.organization.code,))
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(
            [item["id"] for item in content],
            [self.newsfeed[item].id for item in retrieved_newsfeed],
        )
