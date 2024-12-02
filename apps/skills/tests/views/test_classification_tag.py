from unittest.mock import patch
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
from apps.skills.factories import TagClassificationFactory, TagFactory
from apps.skills.models import Tag, TagClassification
from apps.skills.testcases import WikipediaTestCase

faker = Faker()


class CreateClassificationTagTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.tag_classification = TagClassificationFactory(organization=cls.organization)

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
            reverse(
                "ClassificationTag-list",
                args=(
                    self.organization.code,
                    self.tag_classification.id,
                ),
            ),
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
            self.assertIn(self.tag_classification, tag.tag_classifications.all())


class UpdateClassificationTagTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.tag = TagFactory(organization=cls.organization)
        cls.tag_classification = TagClassificationFactory(
            organization=cls.organization, tags=[cls.tag]
        )

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
                "ClassificationTag-detail",
                args=(self.organization.code, self.tag_classification.id, self.tag.id),
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


class DeleteClassificationTagTestCase(JwtAPITestCase):
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
    def test_delete_tag(self, role, expected_code):
        user = self.get_parameterized_test_user(role, instances=[self.organization])
        self.client.force_authenticate(user)
        tag = TagFactory(organization=self.organization)
        self.tag_classification.tags.add(tag)
        response = self.client.delete(
            reverse(
                "ClassificationTag-detail",
                args=(self.organization.code, self.tag_classification.id, tag.id),
            ),
        )
        self.assertEqual(response.status_code, expected_code)
        if expected_code == status.HTTP_204_NO_CONTENT:
            self.assertFalse(Tag.objects.filter(id=tag.id).exists())


class RetrieveClassificationTagTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.tags = TagFactory.create_batch(5, organization=cls.organization)
        cls.unclassified_tags = TagFactory.create_batch(
            5, organization=cls.organization
        )
        cls.other_classification_tags = TagFactory.create_batch(
            5, organization=cls.organization
        )
        cls.tag_classification = TagClassificationFactory(
            organization=cls.organization, tags=cls.tags
        )
        cls.other_tag_classification = TagClassificationFactory(
            organization=cls.organization, tags=cls.other_classification_tags
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
            reverse(
                "ClassificationTag-list",
                args=(
                    self.organization.code,
                    self.tag_classification.id,
                ),
            ),
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
                    "ClassificationTag-detail",
                    args=(self.organization.code, self.tag_classification.id, tag.id),
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


class EnabledClassificationTagTestCase(WikipediaTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.query = faker.word()
        cls.enabled_tags_1 = [
            TagFactory(organization=cls.organization, title_en=f"{cls.query} {i}")
            for i in range(5)
        ]
        cls.enabled_tags_2 = [
            TagFactory(organization=cls.organization, title_en=f"{cls.query} {i}")
            for i in range(5, 10)
        ]
        cls.wikipedia_tags = [
            TagFactory(
                type=Tag.TagType.WIKIPEDIA,
                organization=cls.organization,
                title_en=f"{cls.query} {i}",
            )
            for i in range(10, 15)
        ]
        cls.disabled_tags = [
            TagFactory(organization=cls.organization, title_en=f"{cls.query} {i}")
            for i in range(15, 20)
        ]
        cls.enabled_classification_1 = TagClassificationFactory(
            organization=cls.organization, tags=cls.enabled_tags_1
        )
        cls.enabled_classification_2 = TagClassificationFactory(
            organization=cls.organization, tags=cls.enabled_tags_2
        )
        cls.wikipedia_classification = (
            TagClassification.get_or_create_default_classification(
                classification_type=TagClassification.TagClassificationType.WIKIPEDIA
            )
        )
        cls.wikipedia_classification.tags.add(*cls.wikipedia_tags)
        cls.disabled_classification = TagClassificationFactory(
            organization=cls.organization, tags=cls.disabled_tags
        )
        cls.organization.enabled_projects_tag_classifications.add(
            cls.enabled_classification_1,
            cls.enabled_classification_2,
            cls.wikipedia_classification,
        )
        cls.organization.enabled_skills_tag_classifications.add(
            cls.enabled_classification_1,
            cls.enabled_classification_2,
            cls.wikipedia_classification,
        )

    @parameterized.expand(
        [
            (TagClassification.ReservedSlugs.ENABLED_FOR_PROJECTS,),
            (TagClassification.ReservedSlugs.ENABLED_FOR_SKILLS,),
        ]
    )
    @patch("apps.skills.views.TagViewSet.wikipedia_search")
    def test_list_enabled_tag_classifications(self, enabled_for, mocked_search):
        mocked_search.side_effect = lambda _: None
        response = self.client.get(
            reverse(
                "ClassificationTag-list",
                args=(self.organization.code, enabled_for),
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        mocked_search.assert_has_calls([])
        self.assertSetEqual(
            {tag["id"] for tag in content},
            {
                tag.id
                for tag in self.enabled_tags_1
                + self.enabled_tags_2
                + self.wikipedia_tags
            },
        )

    @parameterized.expand(
        [
            (TagClassification.ReservedSlugs.ENABLED_FOR_PROJECTS,),
            (TagClassification.ReservedSlugs.ENABLED_FOR_SKILLS,),
        ]
    )
    @patch("apps.skills.views.TagViewSet.wikipedia_search")
    def test_search_enabled_tag_classifications(self, enabled_for, mocked_search):
        mocked_search.side_effect = lambda _: None
        response = self.client.get(
            reverse(
                "ClassificationTag-list",
                args=(self.organization.code, enabled_for),
            )
            + f"?search={self.query}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        mocked_search.assert_called_once()
        self.assertSetEqual(
            {tag["id"] for tag in content},
            {
                tag.id
                for tag in self.enabled_tags_1
                + self.enabled_tags_2
                + self.wikipedia_tags
            },
        )

    @parameterized.expand(
        [
            (TagClassification.ReservedSlugs.ENABLED_FOR_PROJECTS,),
            (TagClassification.ReservedSlugs.ENABLED_FOR_SKILLS,),
        ]
    )
    def test_autocomplete_enabled_tag_classifications(self, enabled_for):
        response = self.client.get(
            reverse(
                "ClassificationTag-autocomplete",
                args=(self.organization.code, enabled_for),
            )
            + "?limit=100"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertSetEqual(
            set(content),
            {
                tag.title_en
                for tag in self.enabled_tags_1
                + self.enabled_tags_2
                + self.wikipedia_tags
            },
        )


class SearchClassificationTagTestCase(WikipediaTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.query = faker.word()
        cls.tags = [
            TagFactory(organization=cls.organization, title_en=f"{cls.query} {i}")
            for i in range(5)
        ]
        cls.tag_classification = TagClassificationFactory(
            organization=cls.organization, tags=cls.tags
        )

        cls.existing_wikipedia_tags = [
            TagFactory(type=Tag.TagType.WIKIPEDIA, title_en=f"{cls.query} {i}")
            for i in range(5)
        ]
        cls.existing_not_returned_wikipedia_tags = [
            TagFactory(type=Tag.TagType.WIKIPEDIA, title_en=f"abcd {cls.query} {i}")
            for i in range(5, 10)
        ]
        cls.wikipedia_tag_classification = (
            TagClassification.get_or_create_default_classification(
                classification_type=TagClassification.TagClassificationType.WIKIPEDIA,
            )
        )
        cls.wikipedia_tag_classification.tags.add(
            *cls.existing_wikipedia_tags, *cls.existing_not_returned_wikipedia_tags
        )

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS,),
            (TestRoles.DEFAULT,),
        ]
    )
    def test_search_tags(self, role):
        user = self.get_parameterized_test_user(role)
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse(
                "ClassificationTag-list",
                args=(
                    self.organization.code,
                    self.tag_classification.id,
                ),
            )
            + f"?search={self.query}"
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
    @patch("services.wikipedia.interface.WikipediaService.wbgetentities")
    @patch("services.wikipedia.interface.WikipediaService.wbsearchentities")
    def test_search_wikipedia_tags(self, role, mocked_search, mocked_get):
        existing_tags_qids = [tag.external_id for tag in self.existing_wikipedia_tags]
        new_tags_qids = [self.get_random_wikipedia_qid() for _ in range(45)]
        wikipedia_qids = existing_tags_qids + new_tags_qids
        mocked_search.side_effect = (
            self.search_wikipedia_tag_mocked_side_effect_with_given_ids(wikipedia_qids)
        )
        mocked_get.return_value = self.get_wikipedia_tags_mocked_side_effect(
            wikipedia_qids
        )
        user = self.get_parameterized_test_user(role)
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse(
                "ClassificationTag-list",
                args=(
                    self.organization.code,
                    self.wikipedia_tag_classification.id,
                ),
            )
            + f"?search={self.query}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), 50)
        queryset = Tag.objects.filter(
            type=Tag.TagType.WIKIPEDIA, external_id__in=wikipedia_qids
        )
        self.assertEqual(queryset.count(), len(content))
        self.assertSetEqual(
            {tag["id"] for tag in content}, {tag.id for tag in queryset}
        )

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS,),
            (TestRoles.DEFAULT,),
        ]
    )
    @patch("services.wikipedia.interface.WikipediaService.wbgetentities")
    @patch("services.wikipedia.interface.WikipediaService.wbsearchentities")
    def test_search_wikipedia_tags_pagination(self, role, mocked_search, mocked_get):
        existing_tags_qids = [tag.external_id for tag in self.existing_wikipedia_tags]
        new_tags_qids = [self.get_random_wikipedia_qid() for _ in range(5)]
        wikipedia_qids = existing_tags_qids + new_tags_qids
        mocked_search.side_effect = (
            self.search_wikipedia_tag_mocked_side_effect_with_given_ids(wikipedia_qids)
        )
        mocked_get.return_value = self.get_wikipedia_tags_mocked_side_effect(
            wikipedia_qids
        )
        user = self.get_parameterized_test_user(role)
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse(
                "ClassificationTag-list",
                args=(
                    self.organization.code,
                    self.wikipedia_tag_classification.id,
                ),
            )
            + f"?search={self.query}&limit=10"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertIn("limit=10", content["next"])
        self.assertIn("offset=10", content["next"])
        self.assertEqual(len(content["results"]), 10)
        queryset = Tag.objects.filter(
            type=Tag.TagType.WIKIPEDIA, external_id__in=wikipedia_qids
        )
        self.assertEqual(queryset.count(), len(content["results"]))
        self.assertSetEqual(
            {tag["id"] for tag in content["results"]}, {tag.id for tag in queryset}
        )


class AutocompleteClassificationTagTestCase(JwtAPITestCase):
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

        cls.tag_classification = TagClassificationFactory(
            organization=cls.organization,
            tags=[
                cls.tag_1,
                cls.tag_2,
                cls.tag_3,
                cls.tag_4,
                cls.tag_5,
                *cls.unused_tags,
            ],
        )

        # Attach tags to projects
        cls.project_1.tags.add(cls.tag_1, cls.tag_2, cls.tag_3, cls.tag_4, cls.tag_5)
        cls.project_2.tags.add(cls.tag_1, cls.tag_2, cls.tag_3, cls.tag_4)
        cls.project_3.tags.add(cls.tag_1, cls.tag_2, cls.tag_3)
        cls.project_4.tags.add(cls.tag_1, cls.tag_2)
        cls.project_5.tags.add(cls.tag_1)

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
            reverse(
                "ClassificationTag-autocomplete",
                args=(
                    self.organization.code,
                    self.tag_classification.id,
                ),
            )
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
            reverse(
                "ClassificationTag-autocomplete",
                args=(
                    self.organization.code,
                    self.tag_classification.id,
                ),
            )
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


class ValidateClassificationTagTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.tag_classification = TagClassificationFactory(organization=cls.organization)
        cls.superadmin = UserFactory(groups=[get_superadmins_group()])

    def test_update_non_custom_tag(self):
        tag = TagFactory(organization=self.organization, type=Tag.TagType.ESCO)
        self.tag_classification.tags.add(tag)
        self.client.force_authenticate(self.superadmin)
        payload = {
            "title_fr": faker.sentence(),
        }
        response = self.client.patch(
            reverse(
                "ClassificationTag-detail",
                args=(self.organization.code, self.tag_classification.id, tag.id),
            ),
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
                reverse(
                    "ClassificationTag-list",
                    args=(self.organization.code, self.tag_classification.id),
                ),
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
                reverse(
                    "ClassificationTag-list",
                    args=(self.organization.code, self.tag_classification.id),
                ),
                payload,
            )
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertApiValidationError(
                response,
                {"description": ["Tag description must be 500 characters or less"]},
            )
