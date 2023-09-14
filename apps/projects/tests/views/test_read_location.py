from django.urls import reverse
from rest_framework import status

from apps.commons.test import JwtAPITestCase
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import LocationFactory, ProjectFactory
from apps.projects.models import Project


class ReadLocationTestCase(JwtAPITestCase):
    list_route = "Read-location-list"
    detail_route = "Read-location-detail"
    factory = LocationFactory

    def test_list_anonymous(self):
        project1 = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        project2 = ProjectFactory(publication_status=Project.PublicationStatus.PRIVATE)
        project3 = ProjectFactory(publication_status=Project.PublicationStatus.ORG)
        item1 = self.factory(project=project1)
        self.factory(project=project2)
        self.factory(project=project3)
        response = self.client.get(reverse(self.list_route))
        body = response.json()
        self.assertEqual(response.status_code, status.HTTP_200_OK, body)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(item1.id, body[0]["id"])

    def test_retrieve_public_anonymous(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        instance = self.factory(project=project)
        project_two = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC
        )
        self.factory(project=project_two)
        response = self.client.get(
            reverse(self.detail_route, kwargs={"id": instance.id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        self.assertEqual(instance.id, response.json()["id"])

    def test_retrieve_private_anonymous(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PRIVATE)
        instance = self.factory(project=project)
        project_two = ProjectFactory(
            publication_status=Project.PublicationStatus.PRIVATE
        )
        self.factory(project=project_two)
        response = self.client.get(
            reverse(self.detail_route, kwargs={"id": instance.id})
        )
        self.assertEqual(
            response.status_code, status.HTTP_404_NOT_FOUND, response.json()
        )

    def test_retrieve_org_anonymous(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.ORG)
        instance = self.factory(project=project)
        project_two = ProjectFactory(publication_status=Project.PublicationStatus.ORG)
        self.factory(project=project_two)
        response = self.client.get(
            reverse(self.detail_route, kwargs={"id": instance.id})
        )
        self.assertEqual(
            response.status_code, status.HTTP_404_NOT_FOUND, response.json()
        )

    def test_list_hierarchy_organization(self):
        parent = OrganizationFactory(code="PARENT")
        self.factory(project=ProjectFactory(organizations=[parent]))
        self.factory(
            project=ProjectFactory(organizations=[OrganizationFactory(parent=parent)])
        )
        filters = {"organizations": "PARENT"}
        response = self.client.get(reverse(self.list_route), filters)
        body = response.json()
        self.assertEqual(response.status_code, status.HTTP_200_OK, body)
        self.assertEqual(len(response.json()), 2)
