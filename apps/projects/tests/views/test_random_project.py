from django.urls import reverse
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.commons.test import JwtAPITestCase
from apps.organizations.factories import OrganizationFactory
from apps.projects import factories
from apps.projects.models import Project


class ProjectRandomTestCase(JwtAPITestCase):
    def test_list_anonymous(self):
        projects = factories.ProjectFactory.create_batch(
            10, publication_status=Project.PublicationStatus.PUBLIC
        )
        projects_ids = [p.id for p in projects]

        response = self.client.get(reverse("ProjectRandom-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

        content = response.json()
        self.assertEqual(content["count"], 10)
        random1 = [p["id"] for p in content["results"]]
        self.assertEqual(set(projects_ids), set(random1))

        random2 = [
            p["id"]
            for p in self.client.get(reverse("ProjectRandom-list")).json()["results"]
        ]
        random3 = [
            p["id"]
            for p in self.client.get(reverse("ProjectRandom-list")).json()["results"]
        ]
        self.assertFalse(random1 == random2 == random3)

    def test_list_no_permission(self):
        projects = factories.ProjectFactory.create_batch(
            10, publication_status=Project.PublicationStatus.PUBLIC
        )
        projects_ids = [p.id for p in projects]

        self.client.force_authenticate(UserFactory())
        response = self.client.get(reverse("ProjectRandom-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

        content = response.json()
        self.assertEqual(content["count"], 10)
        random1 = [p["id"] for p in content["results"]]
        self.assertEqual(set(projects_ids), set(random1))

        random2 = [
            p["id"]
            for p in self.client.get(reverse("ProjectRandom-list")).json()["results"]
        ]
        random3 = [
            p["id"]
            for p in self.client.get(reverse("ProjectRandom-list")).json()["results"]
        ]
        self.assertFalse(random1 == random2 == random3)

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
        response = self.client.get(reverse("ProjectRandom-list"), filters)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

        content = response.json()
        self.assertEqual(content["count"], 2)

        self.assertEqual(
            {in_org1.pk, in_org2.pk}, {r["id"] for r in content["results"]}
        )
