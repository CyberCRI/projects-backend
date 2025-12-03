from unittest.mock import patch

from django.urls import reverse
from faker import Faker
from rest_framework import status

from apps.commons.test import JwtAPITestCase, TestRoles
from apps.files.models import ProjectUserAttachmentLink
from apps.files.serializers import ProjectUserAttachmentLinkSerializer

from .mock_response import MockResponse

faker = Faker()


class CreateProjectUserAttachmentLinkTestCase(JwtAPITestCase):

    @patch.object(ProjectUserAttachmentLinkSerializer, "get_url_response")
    def test_create_attachment_link(self, mocked):
        mocked_response = MockResponse()
        mocked.return_value = mocked_response

        user = self.get_parameterized_test_user(TestRoles.DEFAULT)
        self.client.force_authenticate(user)

        payload = {
            "site_url": faker.url(),
        }
        response = self.client.post(
            reverse("ProjectUserAttachmentLink-list", args=(user.id,)),
            data=payload,
        )
        content = response.json()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(content["attachment_type"], "link")
        self.assertEqual(content["site_url"], payload["site_url"])
        self.assertEqual(content["preview_image_url"], mocked_response.image)
        self.assertEqual(content["site_name"], mocked_response.site_name)

    @patch.object(ProjectUserAttachmentLinkSerializer, "get_url_response")
    def test_create_attachment_link_different_user(self, mocked):
        mocked_response = MockResponse()
        mocked.return_value = mocked_response

        user_1 = self.get_parameterized_test_user(TestRoles.DEFAULT)
        user_2 = self.get_parameterized_test_user(TestRoles.DEFAULT)
        self.client.force_authenticate(user_1)

        payload = {
            "site_url": faker.url(),
        }
        response = self.client.post(
            # we try to add attachement on user_2 with user_1 connected
            reverse("ProjectUserAttachmentLink-list", args=(user_2.id,)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class UpdateProjectUserAttachmentLinkTestCase(JwtAPITestCase):
    @patch.object(ProjectUserAttachmentLinkSerializer, "get_url_response")
    def test_update_attachment_link(self, mocked):
        mocked_response = MockResponse()
        mocked.return_value = mocked_response

        user = self.get_parameterized_test_user(TestRoles.DEFAULT)
        self.client.force_authenticate(user)

        link = ProjectUserAttachmentLink.objects.create(title="title", owner=user)

        payload = {"title": "test"}
        response = self.client.patch(
            reverse("ProjectUserAttachmentLink-detail", args=(user.id, link.id)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["title"], payload["title"])

    @patch.object(ProjectUserAttachmentLinkSerializer, "get_url_response")
    def test_update_attachment_link_different_user(self, mocked):
        mocked_response = MockResponse()
        mocked.return_value = mocked_response

        user_1 = self.get_parameterized_test_user(TestRoles.DEFAULT)
        user_2 = self.get_parameterized_test_user(TestRoles.DEFAULT)
        self.client.force_authenticate(user_1)

        link = ProjectUserAttachmentLink.objects.create(title="title", owner=user_1)

        payload = {"title": "test"}
        response = self.client.patch(
            # we try to add attachement on user_2 with user_1 connected
            reverse("ProjectUserAttachmentLink-detail", args=(user_2.id, link.id)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class DeleteProjectUserAttachmentLinkTestCase(JwtAPITestCase):
    def test_delete_attachment_link(self):
        user = self.get_parameterized_test_user(TestRoles.DEFAULT)
        self.client.force_authenticate(user)

        link = ProjectUserAttachmentLink.objects.create(title="title", owner=user)

        response = self.client.delete(
            reverse("ProjectUserAttachmentLink-detail", args=(user.id, link.id)),
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ProjectUserAttachmentLink.objects.filter(id=link.id).exists())

    def test_delete_attachment_link_different_user(self):
        user_1 = self.get_parameterized_test_user(TestRoles.DEFAULT)
        user_2 = self.get_parameterized_test_user(TestRoles.DEFAULT)
        self.client.force_authenticate(user_1)

        link = ProjectUserAttachmentLink.objects.create(title="title", owner=user_1)

        response = self.client.delete(
            # we try to add attachement on user_2 with user_1 connected
            reverse("ProjectUserAttachmentLink-detail", args=(user_2.id, link.id)),
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class GetProjectUserAttachmentLinkTestCase(JwtAPITestCase):
    def test_get_attachment_link_from_annonymous(self):
        user_1 = self.get_parameterized_test_user(TestRoles.DEFAULT)

        user_1_link = ProjectUserAttachmentLink.objects.create(
            title="user_1", owner=user_1
        )

        response = self.client.get(
            reverse("ProjectUserAttachmentLink-list", args=(user_1.id,)),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        link_ids = [obj["id"] for obj in data["results"]]
        self.assertEqual(link_ids, [user_1_link.id])

    def test_get_attachment_link_from_user(self):
        user_1 = self.get_parameterized_test_user(TestRoles.DEFAULT)
        user_2 = self.get_parameterized_test_user(TestRoles.DEFAULT)

        ProjectUserAttachmentLink.objects.create(title="user_1", owner=user_1)
        user_2_link = ProjectUserAttachmentLink.objects.create(
            title="user_2", owner=user_2
        )

        self.client.force_authenticate(user_1)

        response = self.client.get(
            reverse("ProjectUserAttachmentLink-list", args=(user_2.id,)),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        link_ids = [obj["id"] for obj in data["results"]]
        self.assertEqual(link_ids, [user_2_link.id])
