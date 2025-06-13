from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from faker import Faker
from parameterized import parameterized
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase, TestRoles
from apps.files.factories import OrganizationAttachmentFileFactory
from apps.files.models import AttachmentType, OrganizationAttachmentFile
from apps.organizations.factories import OrganizationFactory

faker = Faker()


class CreateOrganizationAttachmentFileTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_201_CREATED),
            (TestRoles.ORG_ADMIN, status.HTTP_201_CREATED),
            (TestRoles.ORG_FACILITATOR, status.HTTP_201_CREATED),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_create_organization_attachment_file(self, role, expected_code):
        user = self.get_parameterized_test_user(role, instances=[self.organization])
        self.client.force_authenticate(user)
        payload = {
            "mime": "text/plain",
            "title": faker.text(max_nb_chars=50),
            "file": SimpleUploadedFile(
                "test_attachment_file.txt",
                b"test attachment file",
                content_type="text/plain",
            ),
            "attachment_type": AttachmentType.FILE,
        }
        response = self.client.post(
            reverse("OrganizationAttachmentFile-list", args=(self.organization.code,)),
            data=payload,
            format="multipart",
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_201_CREATED:
            content = response.json()
            attachment_file = OrganizationAttachmentFile.objects.get(id=content["id"])
            self.assertEqual(attachment_file.organization, self.organization)
            self.assertEqual(content["mime"], payload["mime"])
            self.assertEqual(content["title"], payload["title"])
            with attachment_file.file as file:
                self.assertEqual(file.read(), b"test attachment file")


class UpdateOrganizationAttachmentFileTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.file = OrganizationAttachmentFileFactory(organization=cls.organization)

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_ADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_FACILITATOR, status.HTTP_200_OK),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_update_organization_attachment_file(self, role, expected_code):
        user = self.get_parameterized_test_user(role, instances=[self.organization])
        self.client.force_authenticate(user)
        payload = {"title": faker.text(max_nb_chars=50)}
        response = self.client.patch(
            reverse(
                "OrganizationAttachmentFile-detail",
                args=(self.organization.code, self.file.id),
            ),
            data=payload,
            format="multipart",
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_200_OK:
            content = response.json()
            self.assertEqual(content["title"], payload["title"])


class DeleteOrganizationAttachmentFileTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_ADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_FACILITATOR, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_delete_organization_attachment_file(self, role, expected_code):
        user = self.get_parameterized_test_user(role, instances=[self.organization])
        self.client.force_authenticate(user)
        file = OrganizationAttachmentFileFactory(organization=self.organization)
        response = self.client.delete(
            reverse(
                "OrganizationAttachmentFile-detail",
                args=(self.organization.code, file.id),
            )
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_204_NO_CONTENT:
            self.assertFalse(
                OrganizationAttachmentFile.objects.filter(id=file.id).exists()
            )


class ReadOrganizationAttachmentFileTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.organization_2 = OrganizationFactory()
        cls.files = OrganizationAttachmentFileFactory.create_batch(
            2, organization=cls.organization
        )
        OrganizationAttachmentFileFactory.create_batch(
            2, organization=cls.organization_2
        )

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS,),
            (TestRoles.DEFAULT,),
        ]
    )
    def test_list_organization_attachment_file_unauthorized(self, role):
        user = self.get_parameterized_test_user(role)
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("OrganizationAttachmentFile-list", args=(self.organization.code,))
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), len(self.files))
        self.assertSetEqual(
            {file["id"] for file in content},
            {file.id for file in self.files},
        )

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS,),
            (TestRoles.DEFAULT,),
        ]
    )
    def test_retrieve_organization_attachment_file_unauthorized(self, role):
        user = self.get_parameterized_test_user(role)
        self.client.force_authenticate(user)
        file = self.files[0]
        response = self.client.get(
            reverse(
                "OrganizationAttachmentFile-detail",
                args=(self.organization.code, file.id),
            )
        )
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)


class ValidateAttachmentFileTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.superadmin = UserFactory(groups=[get_superadmins_group()])

    def test_create_identical_files(self):
        self.client.force_authenticate(self.superadmin)
        existing_file = OrganizationAttachmentFileFactory(
            organization=self.organization
        )
        payload = {
            "mime": "text/plain",
            "title": faker.text(max_nb_chars=50),
            "attachment_type": AttachmentType.FILE,
            "file": SimpleUploadedFile(
                "test_attachment_file.txt",
                existing_file.file.read(),
                content_type="text/plain",
            ),
        }
        response = self.client.post(
            reverse("OrganizationAttachmentFile-list", args=(self.organization.code,)),
            data=payload,
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertApiValidationError(
            response,
            {
                "hashcode": [
                    "The file you are trying to upload is already attached to this organization"
                ]
            },
        )

    def test_update_identical_files(self):
        self.client.force_authenticate(self.superadmin)
        file = OrganizationAttachmentFileFactory(organization=self.organization)
        existing_file = OrganizationAttachmentFileFactory(
            organization=self.organization
        )
        payload = {
            "file": SimpleUploadedFile(
                "test_attachment_file.txt",
                existing_file.file.read(),
                content_type="text/plain",
            )
        }
        response = self.client.patch(
            reverse(
                "OrganizationAttachmentFile-detail",
                args=(self.organization.code, file.id),
            ),
            data=payload,
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertApiValidationError(
            response,
            {
                "hashcode": [
                    "The file you are trying to upload is already attached to this organization"
                ]
            },
        )

    def test_update_with_same_file(self):
        self.client.force_authenticate(self.superadmin)
        file = OrganizationAttachmentFileFactory(organization=self.organization)
        payload = {
            "file": SimpleUploadedFile(
                "test_attachment_file.txt",
                file.file.read(),
                content_type="text/plain",
            )
        }
        response = self.client.patch(
            reverse(
                "OrganizationAttachmentFile-detail",
                args=(self.organization.code, file.id),
            ),
            data=payload,
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_duplicate_other_organization(self):
        self.client.force_authenticate(self.superadmin)
        existing_file = OrganizationAttachmentFileFactory(
            organization=self.organization
        )
        organization = OrganizationFactory()
        payload = {
            "mime": "text/plain",
            "title": faker.text(max_nb_chars=50),
            "attachment_type": AttachmentType.FILE,
            "file": SimpleUploadedFile(
                "test_attachment_file.txt",
                existing_file.file.read(),
                content_type="text/plain",
            ),
        }
        response = self.client.post(
            reverse("OrganizationAttachmentFile-list", args=(organization.code,)),
            data=payload,
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
