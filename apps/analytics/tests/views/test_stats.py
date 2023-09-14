import datetime
from collections import defaultdict

from django.urls import reverse
from django.utils.timezone import make_aware

from apps.accounts.factories import UserFactory
from apps.commons.test import JwtAPITestCase
from apps.misc.factories import WikipediaTagFactory
from apps.organizations.factories import OrganizationFactory
from apps.organizations.models import Organization
from apps.projects.factories import ProjectFactory
from apps.projects.models import Project


class StatsTestCaseNoPermission(JwtAPITestCase):
    def test_stats_no_permission(self):
        self.client.force_authenticate(UserFactory())
        response = self.client.get(reverse("Stats-list"))
        self.assertEqual(response.status_code, 403)


class StatsTestCaseCanSeeStats(JwtAPITestCase):
    def test_stats_org_admin(self):
        organization = OrganizationFactory()
        user = UserFactory()
        organization.admins.add(user)
        self.client.force_authenticate(user)
        response = self.client.get(reverse("Stats-list"))
        self.assertEqual(response.status_code, 200)

    def test_stats_org_admin_only_organization_admin_of(self):
        o1 = OrganizationFactory()
        o2 = OrganizationFactory()
        OrganizationFactory()
        OrganizationFactory()
        user = UserFactory()
        o1.admins.add(user)
        o2.admins.add(user)
        self.client.force_authenticate(user)
        response = self.client.get(reverse("Stats-list"))
        self.assertEqual(response.status_code, 200)

        content = response.json()
        self.assertEqual({o["id"] for o in content["by_organization"]}, {o1.pk, o2.pk})

    def test_stats_org_admin_by_organization(self):
        o1 = OrganizationFactory()
        o2 = OrganizationFactory()
        p1 = ProjectFactory()
        p2 = ProjectFactory()
        p3 = ProjectFactory()
        p4 = ProjectFactory()
        o1.projects.add(p1, p2, p3)
        o2.projects.add(p3, p4)
        user = UserFactory()
        o1.admins.add(user)
        o2.admins.add(user)
        self.client.force_authenticate(user)
        response = self.client.get(reverse("Stats-list"))
        self.assertEqual(response.status_code, 200)

        expected = {o1.pk: 3, o2.pk: 2}
        content = response.json()
        self.assertEqual(
            content["by_organization"][0]["project_count"],
            expected[content["by_organization"][0]["id"]],
        )
        self.assertEqual(
            content["by_organization"][1]["project_count"],
            expected[content["by_organization"][1]["id"]],
        )

    def test_stats_org_admin_by_publication_status(self):
        organization = OrganizationFactory()
        p1 = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        p2 = ProjectFactory(publication_status=Project.PublicationStatus.PRIVATE)
        p3 = ProjectFactory(publication_status=Project.PublicationStatus.ORG)
        organization.projects.add(p1, p2, p3)
        user = UserFactory()
        organization.admins.add(user)
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("Stats-list"), {"publication_status": "public"}
        )
        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["by_organization"][0]["project_count"], 1)

        response = self.client.get(
            reverse("Stats-list"), {"publication_status": "private"}
        )
        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["by_organization"][0]["project_count"], 1)

        response = self.client.get(reverse("Stats-list"), {"publication_status": "all"})
        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(content["by_organization"][0]["project_count"], 3)

    def test_stats_org_admin_by_month(self):
        organization = OrganizationFactory()
        projects = ProjectFactory.create_batch(4)
        d1 = make_aware(datetime.datetime(2020, 1, 1))
        d2 = make_aware(datetime.datetime(2020, 2, 1))
        d3 = make_aware(datetime.datetime(2020, 3, 1))
        # Bypass auto_now
        Project.objects.filter(pk=projects[0].pk).update(created_at=d1, updated_at=d1)
        Project.objects.filter(pk=projects[1].pk).update(created_at=d1, updated_at=d3)
        Project.objects.filter(pk=projects[2].pk).update(created_at=d2, updated_at=d3)
        Project.objects.filter(pk=projects[3].pk).update(created_at=d3, updated_at=d3)
        organization.projects.add(*projects)
        user = UserFactory()
        organization.admins.add(user)
        self.client.force_authenticate(user)
        response = self.client.get(reverse("Stats-list"))
        self.assertEqual(response.status_code, 200)

        expected = {
            str(d1.date()): {"created_count": 2, "updated_count": 1},
            str(d2.date()): {"created_count": 1, "updated_count": 0},
            str(d3.date()): {"created_count": 1, "updated_count": 3},
        }
        content = response.json()
        self.assertEqual(
            content["by_month"][0]["created_count"],
            expected[content["by_month"][0]["month"]]["created_count"],
        )
        self.assertEqual(
            content["by_month"][0]["updated_count"],
            expected[content["by_month"][0]["month"]]["updated_count"],
        )
        self.assertEqual(
            content["by_month"][1]["created_count"],
            expected[content["by_month"][1]["month"]]["created_count"],
        )
        self.assertEqual(
            content["by_month"][1]["updated_count"],
            expected[content["by_month"][1]["month"]]["updated_count"],
        )
        self.assertEqual(
            content["by_month"][2]["created_count"],
            expected[content["by_month"][2]["month"]]["created_count"],
        )
        self.assertEqual(
            content["by_month"][2]["updated_count"],
            expected[content["by_month"][2]["month"]]["updated_count"],
        )

    def test_stats_org_admin_by_sdg(self):
        organization = OrganizationFactory()
        p1 = ProjectFactory(sdgs=[1, 2])
        p2 = ProjectFactory(sdgs=[2])
        p3 = ProjectFactory(sdgs=[3])
        organization.projects.add(p1, p2, p3)
        user = UserFactory()
        organization.admins.add(user)
        self.client.force_authenticate(user)
        response = self.client.get(reverse("Stats-list"))
        self.assertEqual(response.status_code, 200)

        expected = defaultdict(int, {1: 1, 2: 2, 3: 1})
        content = response.json()
        for sdg in content["by_sdg"]:
            self.assertEqual(sdg["project_count"], expected[sdg["sdg"]])

    def test_stats_org_admin_top_tags(self):
        organization = OrganizationFactory()
        WikipediaTagFactory.create_batch(10)
        t1 = WikipediaTagFactory()
        t2 = WikipediaTagFactory()
        t3 = WikipediaTagFactory()
        p1 = ProjectFactory()
        p2 = ProjectFactory()
        p3 = ProjectFactory()
        p1.wikipedia_tags.add(t1)
        p2.wikipedia_tags.add(t1, t2)
        p3.wikipedia_tags.add(t3)
        organization.projects.add(p1, p2, p3)
        user = UserFactory()
        organization.admins.add(user)
        self.client.force_authenticate(user)
        response = self.client.get(reverse("Stats-list"))
        self.assertEqual(response.status_code, 200)

        content = response.json()
        self.assertEqual(len(content["top_tags"]), 10)
        for t in content["top_tags"]:
            if t["id"] == t1.pk:
                self.assertEqual(t["project_count"], 2)
                self.assertEqual(set(t["projects"]), {p1.pk, p2.pk})
            if t["id"] == t2.pk:
                self.assertEqual(t["project_count"], 1)
                self.assertEqual(set(t["projects"]), {p2.pk})
            if t["id"] == t3.pk:
                self.assertEqual(t["project_count"], 1)
                self.assertEqual(set(t["projects"]), {p3.pk})


class StatsTestCaseBasePermission(JwtAPITestCase):
    def test_stats_base_permission(self):
        OrganizationFactory()
        user = UserFactory(permissions=[("analytics.view_stat", None)])
        self.client.force_authenticate(user)
        response = self.client.get(reverse("Stats-list"))
        self.assertEqual(response.status_code, 200)

    def test_stats_base_permission_all_organization(self):
        o1 = OrganizationFactory()
        o2 = OrganizationFactory()
        o3 = OrganizationFactory()
        o4 = OrganizationFactory()
        user = UserFactory(permissions=[("analytics.view_stat", None)])
        self.client.force_authenticate(user)
        response = self.client.get(reverse("Stats-list"))
        self.assertEqual(response.status_code, 200)

        content = response.json()
        self.assertEqual(
            {o["id"] for o in content["by_organization"]}, {o1.pk, o2.pk, o3.pk, o4.pk}
        )

    def test_stats_base_permission_by_organization(self):
        o1 = OrganizationFactory()
        o2 = OrganizationFactory()
        p1 = ProjectFactory()
        p2 = ProjectFactory()
        p3 = ProjectFactory()
        p4 = ProjectFactory()
        # Delete organization created by factories
        Organization.objects.exclude(pk__in=[o1.pk, o2.pk]).delete()
        o1.projects.add(p1, p2, p3)
        o2.projects.add(p3, p4)
        user = UserFactory(permissions=[("analytics.view_stat", None)])
        self.client.force_authenticate(user)
        response = self.client.get(reverse("Stats-list"))
        self.assertEqual(response.status_code, 200)

        expected = {o1.pk: 3, o2.pk: 2}
        content = response.json()
        self.assertEqual(
            content["by_organization"][0]["project_count"],
            expected[content["by_organization"][0]["id"]],
        )
        self.assertEqual(
            content["by_organization"][1]["project_count"],
            expected[content["by_organization"][1]["id"]],
        )

    def test_stats_base_permission_by_month(self):
        projects = ProjectFactory.create_batch(4)
        d1 = make_aware(datetime.datetime(2020, 1, 1))
        d2 = make_aware(datetime.datetime(2020, 2, 1))
        d3 = make_aware(datetime.datetime(2020, 3, 1))
        # Bypass auto_now
        Project.objects.filter(pk=projects[0].pk).update(created_at=d1, updated_at=d1)
        Project.objects.filter(pk=projects[1].pk).update(created_at=d1, updated_at=d3)
        Project.objects.filter(pk=projects[2].pk).update(created_at=d2, updated_at=d3)
        Project.objects.filter(pk=projects[3].pk).update(created_at=d3, updated_at=d3)
        user = UserFactory(permissions=[("analytics.view_stat", None)])
        self.client.force_authenticate(user)
        response = self.client.get(reverse("Stats-list"))
        self.assertEqual(response.status_code, 200)

        expected = {
            str(d1.date()): {"created_count": 2, "updated_count": 1},
            str(d2.date()): {"created_count": 1, "updated_count": 0},
            str(d3.date()): {"created_count": 1, "updated_count": 3},
        }
        content = response.json()
        self.assertEqual(
            content["by_month"][0]["created_count"],
            expected[content["by_month"][0]["month"]]["created_count"],
        )
        self.assertEqual(
            content["by_month"][0]["updated_count"],
            expected[content["by_month"][0]["month"]]["updated_count"],
        )
        self.assertEqual(
            content["by_month"][1]["created_count"],
            expected[content["by_month"][1]["month"]]["created_count"],
        )
        self.assertEqual(
            content["by_month"][1]["updated_count"],
            expected[content["by_month"][1]["month"]]["updated_count"],
        )
        self.assertEqual(
            content["by_month"][2]["created_count"],
            expected[content["by_month"][2]["month"]]["created_count"],
        )
        self.assertEqual(
            content["by_month"][2]["updated_count"],
            expected[content["by_month"][2]["month"]]["updated_count"],
        )

    def test_stats_base_permission_by_sdg(self):
        ProjectFactory(sdgs=[1, 2])
        ProjectFactory(sdgs=[2])
        ProjectFactory(sdgs=[3])
        user = UserFactory(permissions=[("analytics.view_stat", None)])
        self.client.force_authenticate(user)
        response = self.client.get(reverse("Stats-list"))
        self.assertEqual(response.status_code, 200)

        expected = defaultdict(int, {1: 1, 2: 2, 3: 1})
        content = response.json()
        for sdg in content["by_sdg"]:
            self.assertEqual(sdg["project_count"], expected[sdg["sdg"]])

    def test_stats_base_permission_top_tags(self):
        WikipediaTagFactory.create_batch(10)
        t1 = WikipediaTagFactory()
        t2 = WikipediaTagFactory()
        t3 = WikipediaTagFactory()
        p1 = ProjectFactory()
        p2 = ProjectFactory()
        p3 = ProjectFactory()
        p1.wikipedia_tags.add(t1)
        p2.wikipedia_tags.add(t1, t2)
        p3.wikipedia_tags.add(t3)
        user = UserFactory(permissions=[("analytics.view_stat", None)])
        self.client.force_authenticate(user)
        response = self.client.get(reverse("Stats-list"))
        self.assertEqual(response.status_code, 200)

        content = response.json()
        self.assertEqual(len(content["top_tags"]), 10)
        for t in content["top_tags"]:
            if t["id"] == t1.pk:
                self.assertEqual(t["project_count"], 2)
                self.assertEqual(set(t["projects"]), {p1.pk, p2.pk})
            if t["id"] == t2.pk:
                self.assertEqual(t["project_count"], 1)
                self.assertEqual(set(t["projects"]), {p2.pk})
            if t["id"] == t3.pk:
                self.assertEqual(t["project_count"], 1)
                self.assertEqual(set(t["projects"]), {p3.pk})
