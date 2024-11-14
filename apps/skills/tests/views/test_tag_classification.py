from django.urls import reverse
from faker import Faker
from parameterized import parameterized
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase, TestRoles
from apps.organizations.factories import OrganizationFactory
from apps.skills.factories import TagClassificationFactory, TagFactory
from apps.skills.models import TagClassification

faker = Faker()


class CreateTagClassificationTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()

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
    def test_create_tag_classification(self, role, expected_code):
        organization = self.organization
        user = self.get_parameterized_test_user(role, instances=[organization])
        self.client.force_authenticate(user)
        payload = {
            "is_public": faker.boolean(),
            "title": faker.word(),
            "description": faker.sentence(),
        }
        response = self.client.post(
            reverse("TagClassification-list", args=(self.organization.code,)),
            payload,
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_201_CREATED:
            content = response.json()
            self.assertEqual(content["title"], payload["title"])
            self.assertEqual(content["description"], payload["description"])
            self.assertEqual(content["is_public"], payload["is_public"])
            tag_classification = TagClassification.objects.get(id=content["id"])
            self.assertEqual(tag_classification.organization, organization)
            self.assertEqual(
                tag_classification.type, TagClassification.TagClassificationType.CUSTOM
            )


class UpdateTagClassificationTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.tag_classification = TagClassificationFactory(organization=cls.organization)

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
    def test_update_tag_classification(self, role, expected_code):
        organization = self.organization
        user = self.get_parameterized_test_user(role, instances=[organization])
        self.client.force_authenticate(user)
        payload = {
            "is_public": faker.boolean(),
            "title": faker.word(),
            "description": faker.sentence(),
        }
        response = self.client.patch(
            reverse(
                "TagClassification-detail",
                args=(organization.code, self.tag_classification.id),
            ),
            payload,
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_200_OK:
            content = response.json()
            self.assertEqual(content["title"], payload["title"])
            self.assertEqual(content["description"], payload["description"])
            self.assertEqual(content["is_public"], payload["is_public"])
            tag_classification = TagClassification.objects.get(id=content["id"])
            self.assertEqual(tag_classification.organization, organization)
            self.assertEqual(
                tag_classification.type, TagClassification.TagClassificationType.CUSTOM
            )


class DeleteTagClassificationTestCase(JwtAPITestCase):
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
    def test_delete_tag_classification(self, role, expected_code):
        organization = self.organization
        tag_classification = TagClassificationFactory(organization=organization)
        user = self.get_parameterized_test_user(role, instances=[organization])
        self.client.force_authenticate(user)
        response = self.client.delete(
            reverse(
                "TagClassification-detail",
                args=(organization.code, tag_classification.id),
            ),
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_204_NO_CONTENT:
            self.assertFalse(
                TagClassification.objects.filter(id=tag_classification.id).exists()
            )


class RetrieveTagClassificationTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.other_organization = OrganizationFactory()

        cls.public_tag_classification = TagClassificationFactory(
            organization=cls.organization, is_public=True
        )
        cls.private_tag_classification = TagClassificationFactory(
            organization=cls.organization, is_public=False
        )
        cls.enabled_tag_classification = TagClassificationFactory(
            organization=cls.organization
        )
        cls.other_organization_public_tag_classification = TagClassificationFactory(
            organization=cls.other_organization, is_public=True
        )
        cls.other_organization_private_tag_classification = TagClassificationFactory(
            organization=cls.other_organization, is_public=False
        )
        cls.other_organization_enabled_public_tag_classification = (
            TagClassificationFactory(
                organization=cls.other_organization, is_public=True
            )
        )
        cls.other_organization_enabled_private_tag_classification = (
            TagClassificationFactory(
                organization=cls.other_organization, is_public=False
            )
        )
        cls.wikipedia_classification = (
            TagClassification.get_or_create_default_classification(
                classification_type=TagClassification.TagClassificationType.WIKIPEDIA
            )
        )
        cls.esco_classification = (
            TagClassification.get_or_create_default_classification(
                classification_type=TagClassification.TagClassificationType.ESCO
            )
        )
        cls.organization.enabled_projects_tag_classifications.add(
            cls.enabled_tag_classification,
            cls.other_organization_enabled_public_tag_classification,
            cls.other_organization_enabled_private_tag_classification,
        )
        cls.organization.enabled_skills_tag_classifications.add(
            cls.enabled_tag_classification,
            cls.other_organization_enabled_public_tag_classification,
            cls.other_organization_enabled_private_tag_classification,
        )
        cls.tag_classifications = [
            cls.public_tag_classification,
            cls.private_tag_classification,
            cls.enabled_tag_classification,
            cls.other_organization_public_tag_classification,
            cls.other_organization_enabled_public_tag_classification,
            cls.wikipedia_classification,
            cls.esco_classification,
        ]
        cls.owned_tags = [
            cls.public_tag_classification,
            cls.private_tag_classification,
            cls.enabled_tag_classification,
        ]
        cls.enabled_tags = [
            cls.enabled_tag_classification,
            cls.other_organization_enabled_public_tag_classification,
            cls.other_organization_enabled_private_tag_classification,
        ]

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS,),
            (TestRoles.DEFAULT,),
            (TestRoles.SUPERADMIN,),
            (TestRoles.ORG_ADMIN,),
            (TestRoles.ORG_FACILITATOR,),
            (TestRoles.ORG_USER,),
        ]
    )
    def test_list_tag_classifications(self, role):
        organization = self.organization
        user = self.get_parameterized_test_user(role, instances=[organization])
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("TagClassification-list", args=(organization.code,))
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), len(self.tag_classifications))
        self.assertSetEqual(
            set(
                tag_classification.id for tag_classification in self.tag_classifications
            ),
            set(tag_classification["id"] for tag_classification in content),
        )
        for tag in content:
            if tag["id"] in [
                tag_classification.id for tag_classification in self.owned_tags
            ]:
                self.assertTrue(tag["is_owned"])
            else:
                self.assertFalse(tag["is_owned"])
            if tag["id"] in [
                tag_classification.id for tag_classification in self.enabled_tags
            ]:
                self.assertTrue(tag["is_enabled_for_projects"])
                self.assertTrue(tag["is_enabled_for_skills"])
            else:
                self.assertFalse(tag["is_enabled_for_projects"])
                self.assertFalse(tag["is_enabled_for_skills"])

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS,),
            (TestRoles.DEFAULT,),
            (TestRoles.SUPERADMIN,),
            (TestRoles.ORG_ADMIN,),
            (TestRoles.ORG_FACILITATOR,),
            (TestRoles.ORG_USER,),
        ]
    )
    def test_retrieve_tag_classification(self, role):
        organization = self.organization
        user = self.get_parameterized_test_user(role, instances=[organization])
        self.client.force_authenticate(user)
        for tag_classification in self.tag_classifications:
            response = self.client.get(
                reverse(
                    "TagClassification-detail",
                    args=(organization.code, tag_classification.id),
                )
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            content = response.json()
            self.assertEqual(content["id"], tag_classification.id)


class AddTagsToTagClassificationTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.tag_classification = TagClassificationFactory(organization=cls.organization)

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
    def test_add_tags_to_tag_classification(self, role, expected_code):
        organization = self.organization
        user = self.get_parameterized_test_user(role, instances=[organization])
        self.client.force_authenticate(user)
        tags = TagFactory.create_batch(3, organization=organization)
        payload = {
            "tags": [tag.id for tag in tags],
        }
        response = self.client.post(
            reverse(
                "TagClassification-add-tags",
                args=(organization.code, self.tag_classification.id),
            ),
            payload,
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_204_NO_CONTENT:
            self.tag_classification.refresh_from_db()
            tag_classification_tags = self.tag_classification.tags.all()
            for tag in tags:
                self.assertIn(tag, tag_classification_tags)


class RemoveTagsFromTagClassificationTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.tag_classification = TagClassificationFactory(organization=cls.organization)

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
    def test_add_tags_to_tag_classification(self, role, expected_code):
        organization = self.organization
        user = self.get_parameterized_test_user(role, instances=[organization])
        self.client.force_authenticate(user)
        tags = TagFactory.create_batch(3, organization=organization)
        self.tag_classification.tags.add(*tags)
        payload = {
            "tags": [tag.id for tag in tags],
        }
        response = self.client.post(
            reverse(
                "TagClassification-remove-tags",
                args=(organization.code, self.tag_classification.id),
            ),
            payload,
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_204_NO_CONTENT:
            self.tag_classification.refresh_from_db()
            tag_classification_tags = self.tag_classification.tags.all()
            for tag in tags:
                self.assertNotIn(tag, tag_classification_tags)


class ValidateTagClassificationTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.tag_classification = TagClassificationFactory(organization=cls.organization)
        cls.superadmin = UserFactory(groups=[get_superadmins_group()])

    def test_add_tag_from_other_organization(self):
        self.client.force_authenticate(self.superadmin)
        tag = TagFactory(organization=OrganizationFactory())
        payload = {
            "tags": [tag.id],
        }
        response = self.client.post(
            reverse(
                "TagClassification-add-tags",
                args=(self.organization.code, self.tag_classification.id),
            ),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertApiValidationError(
            response,
            {"tags": ["Tags must belong to the classification's organization"]},
        )


class MiscTagClassificationTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.superadmin = UserFactory(groups=[get_superadmins_group()])

    def test_get_slug(self):
        title = "My AMazing TaG ClassIFicatIOn !"
        tag_classification = TagClassificationFactory(
            title=title, organization=self.organization
        )
        self.assertEqual(tag_classification.slug, "my-amazing-tag-classification")
        tag_classification = TagClassificationFactory(
            title=title, organization=self.organization
        )
        self.assertEqual(tag_classification.slug, "my-amazing-tag-classification-1")
        tag_classification = TagClassificationFactory(
            title=title, organization=self.organization
        )
        self.assertEqual(tag_classification.slug, "my-amazing-tag-classification-2")
        tag_classification = TagClassificationFactory(
            title="123", organization=self.organization
        )
        self.assertTrue(
            tag_classification.slug.startswith("tag-classification-"),
            tag_classification.slug,
        )

    def test_multiple_lookups(self):
        tag_classification = TagClassificationFactory(organization=self.organization)
        response = self.client.get(
            reverse(
                "TagClassification-detail",
                args=(self.organization.code, tag_classification.id),
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["slug"], tag_classification.slug)
        response = self.client.get(
            reverse(
                "TagClassification-detail",
                args=(self.organization.code, tag_classification.slug),
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], tag_classification.id)

    def test_validate_title_too_long(self):
        self.client.force_authenticate(self.superadmin)
        payload = {
            "title": 51 * "*",
            "description": faker.sentence(),
        }
        response = self.client.post(
            reverse(
                "TagClassification-list",
                args=(self.organization.code,),
            ),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertApiValidationError(
            response, {"title": ["Ensure this field has no more than 50 characters."]}
        )

    def test_validate_description_too_long(self):
        self.client.force_authenticate(self.superadmin)
        payload = {
            "title": faker.word(),
            "description": 501 * "*",
        }
        response = self.client.post(
            reverse(
                "TagClassification-list",
                args=(self.organization.code,),
            ),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertApiValidationError(
            response,
            {"description": ["Ensure this field has no more than 500 characters."]},
        )
