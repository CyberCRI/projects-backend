import bisect
import random

from django.conf import settings
from django.test import override_settings
from django.urls import reverse
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.analytics.factories import StatFactory
from apps.commons.test import JwtAPITestCase
from apps.organizations.factories import OrganizationFactory
from apps.projects import factories
from apps.projects.models import Project
from apps.projects.recommendations import top_project
from services.mixpanel.factories import MixpanelEventFactory


class ProjectTopTestCase(JwtAPITestCase):
    def test_list_anonymous(self):
        public = factories.ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC
        )
        factories.ProjectFactory(publication_status=Project.PublicationStatus.PRIVATE)
        factories.ProjectFactory(publication_status=Project.PublicationStatus.ORG)
        response = self.client.get(reverse("ProjectTop-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

        content = response.json()
        self.assertEqual(content["count"], 1)

        _, scores = top_project(Project.objects.all())
        result = content["results"][0]
        self.assertEqual(public.pk, result["id"])
        self.assertEqual(public.title, result["title"])
        self.assertEqual(public.purpose, result["purpose"])
        self.assertEqual(public.language, result["language"])
        self.assertEqual(scores[public.pk], result["score"])
        self.assertEqual(
            set(public.categories.all().values_list("id", flat=True)),
            set([c["id"] for c in result["categories"]]),
        )

    def test_list_no_permission(self):
        public = factories.ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC
        )
        private = factories.ProjectFactory(
            publication_status=Project.PublicationStatus.PRIVATE
        )
        org = factories.ProjectFactory(publication_status=Project.PublicationStatus.ORG)
        StatFactory(project=public)
        StatFactory(project=private)
        StatFactory(project=org)
        self.client.force_authenticate(UserFactory())
        response = self.client.get(reverse("ProjectTop-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

        content = response.json()
        self.assertEqual(content["count"], 1)

        _, scores = top_project(Project.objects.all())
        result = content["results"][0]
        self.assertEqual(public.pk, result["id"])
        self.assertEqual(public.title, result["title"])
        self.assertEqual(public.purpose, result["purpose"])
        self.assertEqual(public.language, result["language"])
        # TODO: Understand why `nb_updates` jump from 2 to 29512 when authenticating a user with no right
        # self.assertEqual(scores[public.pk], result["score"])  # noqa
        self.assertEqual(
            set(public.categories.all().values_list("id", flat=True)),
            set([c["id"] for c in result["categories"]]),
        )

    def test_list_org_permission(self):
        public = factories.ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC
        )
        factories.ProjectFactory(publication_status=Project.PublicationStatus.PRIVATE)
        private_in_org = factories.ProjectFactory(
            publication_status=Project.PublicationStatus.PRIVATE
        )
        has_perm = factories.ProjectFactory(
            publication_status=Project.PublicationStatus.PRIVATE
        )
        factories.ProjectFactory(publication_status=Project.PublicationStatus.ORG)
        in_org = factories.ProjectFactory(
            publication_status=Project.PublicationStatus.ORG
        )
        organization = OrganizationFactory()
        organization.projects.add(in_org, private_in_org)
        user = UserFactory(
            permissions=[
                ("projects.view_project", has_perm),
                ("organizations.view_org_project", organization),
            ]
        )
        self.client.force_authenticate(user)
        response = self.client.get(reverse("ProjectTop-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

        content = response.json()
        self.assertEqual(content["count"], 3)
        self.assertEqual(
            {public.pk, has_perm.pk, in_org.pk}, {r["id"] for r in content["results"]}
        )

    def test_list_filter_organization(self):
        organization1 = OrganizationFactory()
        organization2 = OrganizationFactory()
        organization3 = OrganizationFactory()
        in_org1 = factories.ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
        )
        in_org2 = factories.ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
        )
        in_org3 = factories.ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
        )
        factories.ProjectFactory(publication_status=Project.PublicationStatus.PRIVATE)
        in_org1.organizations.add(organization1)
        in_org2.organizations.add(organization2)
        in_org3.organizations.add(organization3)

        filters = {"organizations": f"{organization1.code},{organization2.code}"}
        response = self.client.get(reverse("ProjectTop-list"), filters)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

        content = response.json()
        self.assertEqual(content["count"], 2)

        self.assertEqual(
            {in_org1.pk, in_org2.pk}, {r["id"] for r in content["results"]}
        )

    @override_settings(
        MIDDLEWARE=[
            m
            for m in settings.MIDDLEWARE
            if m != "projects.middlewares.PerRequestClearMiddleware"
        ]
    )
    def test_views_in_response(self):
        project = factories.ProjectFactory.create(description="")
        MixpanelEventFactory.create_batch(10, project=project)

        response = self.client.get(reverse("ProjectTop-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

        results = response.json()["results"]
        self.assertEqual(project.get_views(), results[0]["views"])

    @override_settings(
        MIDDLEWARE=[
            m
            for m in settings.MIDDLEWARE
            if m != "projects.middlewares.PerRequestClearMiddleware"
        ]
    )
    def test_order(self):
        projects = factories.ProjectFactory.create_batch(10, description="")
        views_sample = random.sample(range(1000), 10)
        order = []
        for i, p in enumerate(projects):
            views = views_sample[i]
            MixpanelEventFactory.create_batch(views, project=p)
            bisect.insort(order, (views, p))
        order = [t[1] for t in reversed(order)]

        response = self.client.get(reverse("ProjectTop-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

        results = response.json()["results"]
        for i in range(10):
            self.assertEqual(order[i].pk, results[i]["id"])

    @override_settings(
        MIDDLEWARE=[
            m
            for m in settings.MIDDLEWARE
            if m != "projects.middlewares.PerRequestClearMiddleware"
        ]
    )
    def test_order_one_organization(self):
        organization1 = OrganizationFactory()
        organization2 = OrganizationFactory()
        in_org1 = factories.ProjectFactory.create_batch(5, description="")
        in_org2 = factories.ProjectFactory.create_batch(5, description="")
        organization1.projects.add(*in_org1)
        organization2.projects.add(*in_org2)

        views_sample = random.sample(range(1000), 10)
        order = []
        for i, p in enumerate(in_org1):
            views = views_sample[i]
            MixpanelEventFactory.create_batch(
                views, project=p, organization=organization1
            )
            bisect.insort(order, (views, p))
        for i, p in enumerate(in_org2):
            views = views_sample[i + 5]
            MixpanelEventFactory.create_batch(
                views, project=p, organization=organization2
            )
        order = [t[1] for t in reversed(order)]
        filters = {"organizations": f"{organization1.code}"}
        response = self.client.get(reverse("ProjectTop-list"), filters)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

        content = response.json()
        self.assertEqual(content["count"], 5)
        for i in range(5):
            self.assertEqual(order[i].pk, content["results"][i]["id"])

    @override_settings(
        MIDDLEWARE=[
            m
            for m in settings.MIDDLEWARE
            if m != "projects.middlewares.PerRequestClearMiddleware"
        ]
    )
    def test_order_multiple_organization(self):
        organization1 = OrganizationFactory()
        organization2 = OrganizationFactory()
        organization3 = OrganizationFactory()
        in_org1 = factories.ProjectFactory.create_batch(3, description="")
        in_org2 = factories.ProjectFactory.create_batch(3, description="")
        in_org3 = factories.ProjectFactory.create_batch(3, description="")
        organization1.projects.add(*in_org1)
        organization2.projects.add(*in_org2)
        organization3.projects.add(*in_org3)

        views_sample = random.sample(range(1000), 9)
        order = []
        for i, p in enumerate(in_org1):
            views = views_sample[i]
            MixpanelEventFactory.create_batch(
                views, project=p, organization=organization1
            )
            bisect.insort(order, (views, p))
        for i, p in enumerate(in_org2):
            views = views_sample[i + 3]
            MixpanelEventFactory.create_batch(
                views, project=p, organization=organization2
            )
        for i, p in enumerate(in_org3):
            views = views_sample[i + 6]
            MixpanelEventFactory.create_batch(
                views, project=p, organization=organization3
            )
            bisect.insort(order, (views, p))
        order = [t[1] for t in reversed(order)]

        filters = {"organizations": f"{organization1.code},{organization3.code}"}
        response = self.client.get(reverse("ProjectTop-list"), filters)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

        content = response.json()
        self.assertEqual(content["count"], 6)
        for i in range(6):
            self.assertEqual(order[i].pk, content["results"][i]["id"])

    def test_list_default_organization(self):
        parent = OrganizationFactory(code="PARENT")
        factories.ProjectFactory(organizations=[parent])
        factories.ProjectFactory(organizations=[OrganizationFactory(parent=parent)])
        filters = {"organizations": "PARENT"}
        response = self.client.get(reverse("ProjectTop-list"), filters)
        content = response.json()
        self.assertEqual(response.status_code, status.HTTP_200_OK, content)
        self.assertEqual(content["count"], 2)
