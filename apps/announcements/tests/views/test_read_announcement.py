from django.urls import reverse
from rest_framework import status

from apps.announcements.factories import AnnouncementFactory
from apps.commons.test import JwtAPITestCase
from apps.projects.factories import ProjectFactory
from apps.projects.models import Project


class ReadAnnouncementTestCase(JwtAPITestCase):
    list_route = "Read-announcement-list"
    detail_route = "Read-announcement-detail"
    factory = AnnouncementFactory

    def test_list_anonymous(self):
        project1 = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        project2 = ProjectFactory(publication_status=Project.PublicationStatus.PRIVATE)
        project3 = ProjectFactory(publication_status=Project.PublicationStatus.ORG)
        item1 = self.factory(project=project1)
        item2 = self.factory(project=project2)
        item3 = self.factory(project=project3)
        response = self.client.get(reverse(self.list_route))
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        self.assertEqual(response.json()["count"], 3)
        self.assertEqual(
            sorted([item1.id, item2.id, item3.id]),
            sorted([i["id"] for i in response.json()["results"]]),
        )

    def test_retrieve_public_anonymous(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        instance = self.factory(project=project)
        response = self.client.get(
            reverse(self.detail_route, kwargs={"id": instance.id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        self.assertEqual(instance.id, response.json()["id"])

    def test_retrieve_private_anonymous(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PRIVATE)
        instance = self.factory(project=project)
        response = self.client.get(
            reverse(self.detail_route, kwargs={"id": instance.id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        self.assertEqual(instance.id, response.json()["id"])

    def test_retrieve_org_anonymous(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.ORG)
        instance = self.factory(project=project)
        response = self.client.get(
            reverse(self.detail_route, kwargs={"id": instance.id})
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.json())
        self.assertEqual(instance.id, response.json()["id"])
