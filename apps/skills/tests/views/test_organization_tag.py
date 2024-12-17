from uuid import UUID

from django.urls import reverse
from faker import Faker
from parameterized import parameterized
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase, TestRoles
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory
from apps.skills.factories import TagFactory
from apps.skills.models import Tag

faker = Faker()


class CreateOrganizationTagTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()

    @staticmethod
    def is_valid_uuid(uuid):
        try:
            UUID(uuid)
            return True
        except ValueError:
            return False

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_201_CREATED),
            (TestRoles.ORG_ADMIN, status.HTTP_201_CREATED),
            (TestRoles.ORG_FACILITATOR, status.HTTP_403_FORBIDDEN),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_create_tag(self, role, expected_code):
        organization = self.organization
        user = self.get_parameterized_test_user(role, instances=[organization])
        self.client.force_authenticate(user)
        payload = {
            "title_fr": faker.word(),
            "title_en": faker.word(),
            "description_fr": faker.sentence(),
            # description_en uses the same value as description_fr if not provided
        }
        response = self.client.post(
            reverse("OrganizationTag-list", args=(self.organization.code,)),
            payload,
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_201_CREATED:
            content = response.json()
            self.assertEqual(content["title_fr"], payload["title_fr"])
            self.assertEqual(content["title_en"], payload["title_en"])
            self.assertEqual(content["title"], payload["title_en"])
            self.assertEqual(content["description_fr"], payload["description_fr"])
            self.assertEqual(content["description_en"], payload["description_fr"])
            self.assertEqual(content["description"], payload["description_fr"])
            tag = Tag.objects.get(id=content["id"])
            self.assertEqual(tag.organization, organization)
            self.assertTrue(self.is_valid_uuid(tag.external_id))


class UpdateOrganizationTagTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.tag = TagFactory(organization=cls.organization)

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_ADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_FACILITATOR, status.HTTP_403_FORBIDDEN),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_update_tag(self, role, expected_code):
        user = self.get_parameterized_test_user(role, instances=[self.organization])
        self.client.force_authenticate(user)
        payload = {
            "title_fr": faker.word(),
            "title_en": faker.word(),
            "description_fr": faker.sentence(),
            "description_en": faker.sentence(),
        }
        response = self.client.patch(
            reverse(
                "OrganizationTag-detail", args=(self.organization.code, self.tag.id)
            ),
            payload,
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_200_OK:
            content = response.json()
            self.assertEqual(content["title_fr"], payload["title_fr"])
            self.assertEqual(content["title_en"], payload["title_en"])
            self.assertEqual(content["title"], payload["title_en"])
            self.assertEqual(content["description_fr"], payload["description_fr"])
            self.assertEqual(content["description_en"], payload["description_en"])
            self.assertEqual(content["description"], payload["description_en"])


class DeleteOrganizationTagTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_ADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_FACILITATOR, status.HTTP_403_FORBIDDEN),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_delete_tag(self, role, expected_code):
        user = self.get_parameterized_test_user(role, instances=[self.organization])
        self.client.force_authenticate(user)
        tag = TagFactory(organization=self.organization)
        response = self.client.delete(
            reverse("OrganizationTag-detail", args=(self.organization.code, tag.id)),
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_204_NO_CONTENT:
            self.assertFalse(Tag.objects.filter(id=tag.id).exists())


class RetrieveOrganizationTagTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.other_organization = OrganizationFactory()
        cls.tags = TagFactory.create_batch(5, organization=cls.organization)
        cls.other_organization_tags = TagFactory.create_batch(
            5, organization=cls.other_organization
        )

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS,),
            (TestRoles.DEFAULT,),
        ]
    )
    def test_list_tags(self, role):
        user = self.get_parameterized_test_user(role)
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("OrganizationTag-list", args=(self.organization.code,)),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), len(self.tags))
        self.assertSetEqual(
            {tag["id"] for tag in content},
            {tag.id for tag in self.tags},
        )

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS,),
            (TestRoles.DEFAULT,),
        ]
    )
    def test_retrieve_tag(self, role):
        user = self.get_parameterized_test_user(role)
        self.client.force_authenticate(user)
        for tag in self.tags:
            response = self.client.get(
                reverse(
                    "OrganizationTag-detail", args=(self.organization.code, tag.id)
                ),
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            content = response.json()
            self.assertEqual(content["title_fr"], tag.title_fr)
            self.assertEqual(content["title_en"], tag.title_en)
            self.assertEqual(content["title"], tag.title_en)
            self.assertEqual(content["description_fr"], tag.description_fr)
            self.assertEqual(content["description_en"], tag.description_en)
            self.assertEqual(content["description"], tag.description_en)


class AutocompleteOrganizationTagTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()

        cls.query = faker.word()
        cls.tag_1 = TagFactory(organization=cls.organization, title_en=cls.query)
        cls.tag_2 = TagFactory(
            organization=cls.organization, title_en=f"{cls.query} abcd"
        )
        cls.tag_3 = TagFactory(
            organization=cls.organization, title_en=f"{cls.query}_abcd"
        )
        cls.tag_4 = TagFactory(
            organization=cls.organization, title_en=f"{cls.query}abcd"
        )
        cls.tag_5 = TagFactory(
            organization=cls.organization, title_en=f"abcd {cls.query}"
        )

        # Projects to which the tags are attached for ordering
        cls.project_1 = ProjectFactory(organizations=[cls.organization])
        cls.project_2 = ProjectFactory(organizations=[cls.organization])
        cls.project_3 = ProjectFactory(organizations=[cls.organization])
        cls.project_4 = ProjectFactory(organizations=[cls.organization])
        cls.project_5 = ProjectFactory(organizations=[cls.organization])

        # Other tags returned by the autocomplete endpoint
        cls.unused_tags = [
            TagFactory(organization=cls.organization, title_en=f"{cls.query} {i}")
            for i in range(5)
        ]

        # Other tags not returned by the autocomplete endpoint
        not_returned = [
            TagFactory(title_en=f"abcd{cls.query}"),
            *TagFactory.create_batch(5),
        ]

        # Attach tags to projects
        cls.project_1.tags.add(
            cls.tag_1, cls.tag_2, cls.tag_3, cls.tag_4, cls.tag_5, *not_returned
        )
        cls.project_2.tags.add(
            cls.tag_1, cls.tag_2, cls.tag_3, cls.tag_4, *not_returned
        )
        cls.project_3.tags.add(cls.tag_1, cls.tag_2, cls.tag_3, *not_returned)
        cls.project_4.tags.add(cls.tag_1, cls.tag_2, *not_returned)
        cls.project_5.tags.add(cls.tag_1, *not_returned)

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS,),
            (TestRoles.DEFAULT,),
        ]
    )
    def test_autocomplete_default_limit(self, role):
        user = self.get_parameterized_test_user(role)
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("OrganizationTag-autocomplete", args=(self.organization.code,))
            + f"?search={self.query}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(len(content), 5)
        self.assertListEqual(
            content,
            [
                self.tag_1.title_en,
                self.tag_2.title_en,
                self.tag_3.title_en,
                self.tag_4.title_en,
                self.tag_5.title_en,
            ],
        )

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS,),
            (TestRoles.DEFAULT,),
        ]
    )
    def test_autocomplete_custom_limit(self, role):
        user = self.get_parameterized_test_user(role)
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("OrganizationTag-autocomplete", args=(self.organization.code,))
            + f"?query={self.query}&limit=10"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(len(content), 10)
        self.assertListEqual(
            content[:5],
            [
                self.tag_1.title_en,
                self.tag_2.title_en,
                self.tag_3.title_en,
                self.tag_4.title_en,
                self.tag_5.title_en,
            ],
        )
        self.assertSetEqual(set(content[5:]), {tag.title for tag in self.unused_tags})


class ValidateOrganizationTagTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.superadmin = UserFactory(groups=[get_superadmins_group()])

    def test_update_non_custom_tag(self):
        tag = TagFactory(organization=self.organization, type=Tag.TagType.ESCO)
        self.client.force_authenticate(self.superadmin)
        payload = {
            "title_fr": faker.sentence(),
        }
        response = self.client.patch(
            reverse("OrganizationTag-detail", args=(self.organization.code, tag.id)),
            payload,
        )
        self.assertApiTechnicalError(
            response,
            "Only custom tags can be updated",
        )

    def test_validate_title_too_long(self):
        self.client.force_authenticate(self.superadmin)
        for title_field in ["title_fr", "title_en", "title"]:
            payload = {
                title_field: 51 * "*",
                "description": faker.sentence(),
            }
            response = self.client.post(
                reverse("OrganizationTag-list", args=(self.organization.code,)),
                payload,
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertApiValidationError(
                response,
                {"title": ["Tag title must be 50 characters or less"]},
            )

    def test_validate_description_too_long(self):
        self.client.force_authenticate(self.superadmin)
        for description_field in ["description_fr", "description_en", "description"]:
            payload = {
                "title": faker.word(),
                description_field: 501 * "*",
            }
            response = self.client.post(
                reverse("OrganizationTag-list", args=(self.organization.code,)),
                payload,
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertApiValidationError(
                response,
                {"description": ["Tag description must be 500 characters or less"]},
            )
