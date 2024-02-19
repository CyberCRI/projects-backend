from unittest.mock import patch

from django.urls import reverse
from faker import Faker
from parameterized import parameterized
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase, TestRoles
from apps.files.enums import AttachmentLinkCategory
from apps.files.factories import AttachmentLinkFactory
from apps.files.models import AttachmentLink
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory
from apps.projects.models import Project

from .mock_response import MockResponse

faker = Faker()


class CreateAttachmentLinkTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
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
    @patch("apps.files.serializers.AttachmentLinkSerializer.get_url_response")
    def test_create_attachment_link(self, role, expected_code, mocked):
        mocked_response = MockResponse()
        mocked.return_value = mocked_response
        project = self.project
        user = self.get_parameterized_test_user(role, instances=[project])
        self.client.force_authenticate(user)
        payload = {
            "site_url": faker.url(),
            "project_id": project.id,
        }
        response = self.client.post(
            reverse("AttachmentLink-list", args=(project.id,)), data=payload
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_201_CREATED:
            content = response.json()
            assert content["attachment_type"] == "link"
            assert content["site_url"] == payload["site_url"]
            assert content["preview_image_url"] == mocked_response.image
            assert content["site_name"] == mocked_response.site_name


class UpdateAttachmentLinkTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.project = ProjectFactory(organizations=[cls.organization])
        cls.link = AttachmentLinkFactory(
            project=cls.project, category=AttachmentLinkCategory.OTHER
        )

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
    def test_update_attachment_link(self, role, expected_code):
        user = self.get_parameterized_test_user(role, instances=[self.project])
        self.client.force_authenticate(user)
        payload = {"category": AttachmentLinkCategory.TOOL}
        response = self.client.patch(
            reverse("AttachmentLink-detail", args=(self.project.id, self.link.id)),
            data=payload,
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_200_OK:
            content = response.json()
            assert content["category"] == payload["category"]


class DeleteAttachmentLinkTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
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
    def test_delete_attachment_link(self, role, expected_code):
        project = self.project
        user = self.get_parameterized_test_user(role, instances=[project])
        self.client.force_authenticate(user)
        link = AttachmentLinkFactory(project=project)
        response = self.client.delete(
            reverse("AttachmentLink-detail", args=(project.id, link.id)),
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_204_NO_CONTENT:
            assert not AttachmentLink.objects.filter(id=link.id).exists()


class ListAttachmentLinkTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.projects = {
            "public": ProjectFactory(
                publication_status=Project.PublicationStatus.PUBLIC,
                organizations=[cls.organization],
            ),
            "org": ProjectFactory(
                publication_status=Project.PublicationStatus.ORG,
                organizations=[cls.organization],
            ),
            "private": ProjectFactory(
                publication_status=Project.PublicationStatus.PRIVATE,
                organizations=[cls.organization],
            ),
        }
        cls.links = {
            "public": AttachmentLinkFactory(project=cls.projects["public"]),
            "org": AttachmentLinkFactory(project=cls.projects["org"]),
            "private": AttachmentLinkFactory(project=cls.projects["private"]),
        }

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, ("public",)),
            (TestRoles.DEFAULT, ("public",)),
            (TestRoles.SUPERADMIN, ("public", "org", "private")),
            (TestRoles.ORG_ADMIN, ("public", "org", "private")),
            (TestRoles.ORG_FACILITATOR, ("public", "org", "private")),
            (TestRoles.ORG_USER, ("public", "org")),
            (TestRoles.PROJECT_MEMBER, ("public", "org", "private")),
            (TestRoles.PROJECT_OWNER, ("public", "org", "private")),
            (TestRoles.PROJECT_REVIEWER, ("public", "org", "private")),
        ]
    )
    def test_list_attachment_links(self, role, retrieved_links):
        user = self.get_parameterized_test_user(
            role, instances=list(self.projects.values())
        )
        self.client.force_authenticate(user)
        for publication_status, project in self.projects.items():
            response = self.client.get(
                reverse(
                    "AttachmentLink-list",
                    args=(project.id,),
                ),
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            content = response.json()["results"]
            if publication_status in retrieved_links:
                assert len(content) == 1
                assert content[0]["id"] == self.links[publication_status].id
            else:
                assert len(content) == 0


class ValidateAttachmentLinkTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.project = ProjectFactory(organizations=[cls.organization])
        cls.domain = faker.domain_name()
        cls.url = f"https://{cls.domain}"
        cls.link = AttachmentLinkFactory(site_url=cls.url, project=cls.project)

    def test_create_duplicate_domain(self):
        user = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(user)
        payload = {"site_url": self.url, "project_id": self.project.id}
        response = self.client.post(
            reverse("AttachmentLink-list", args=(self.project.id,)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        content = response.json()
        assert content == {
            "non_field_errors": ["This url is already attached to this project."]
        }

    @patch("apps.files.serializers.AttachmentLinkSerializer.get_url_response")
    def test_create_duplicate_www_domain(self, mocked):
        mocked.return_value = MockResponse()
        user = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(user)
        www_url = f"https://www.{self.domain}"
        payload = {"site_url": www_url, "project_id": self.project.id}
        response = self.client.post(
            reverse("AttachmentLink-list", args=(self.project.id,)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_patch_duplicate_link(self):
        user = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(user)
        link = AttachmentLinkFactory(project=self.project)
        payload = {"site_url": self.url, "project_id": self.project.id}
        response = self.client.patch(
            reverse("AttachmentLink-detail", args=(self.project.id, link.id)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        content = response.json()
        assert content == {
            "non_field_errors": ["This url is already attached to this project."]
        }

    @patch("apps.files.serializers.AttachmentLinkSerializer.get_url_response")
    def test_create_duplicate_other_project(self, mocked):
        mocked.return_value = MockResponse()
        user = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(user)
        project = ProjectFactory(organizations=[self.organization])
        payload = {"site_url": self.url, "project_id": project.id}
        response = self.client.post(
            reverse("AttachmentLink-list", args=(project.id,)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
