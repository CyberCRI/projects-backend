from unittest.mock import patch

from django.urls import reverse
from faker import Faker
from parameterized import parameterized
from rest_framework import status

from apps.commons.test import JwtAPITestCase, TestRoles
from apps.organizations.factories import OrganizationFactory
from apps.search.testcases import SearchTestCaseMixin
from apps.skills.factories import TagClassificationFactory, TagFactory
from apps.skills.models import Tag, TagClassification
from apps.skills.testcases import WikipediaTestCase

faker = Faker()


class SearchOrganizationTagTestCase(JwtAPITestCase, SearchTestCaseMixin):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.query = faker.word()
        cls.tag_1 = TagFactory(
            organization=cls.organization,
            title_en=cls.query,
            title_fr="",
            description_en="",
            description_fr="",
        )
        cls.tag_2 = TagFactory(
            organization=cls.organization,
            description_en=cls.query,
            title_en="",
            title_fr="",
            description_fr="",
        )
        cls.tag_3 = TagFactory(
            organization=cls.organization,
            title_fr=cls.query,
            title_en="",
            description_en="",
            description_fr="",
        )
        cls.tag_4 = TagFactory(
            organization=cls.organization,
            description_fr=cls.query,
            title_en="",
            title_fr="",
            description_en="",
        )
        # Order tags by search relevance
        cls.tags = [cls.tag_1, cls.tag_3, cls.tag_2, cls.tag_4]
        cls.other_tags = TagFactory.create_batch(
            5,
            organization=cls.organization,
            title_en="",
            title_fr="",
            description_en="",
            description_fr="",
        )

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS,),
            (TestRoles.DEFAULT,),
        ]
    )
    @patch("apps.search.interface.OpenSearchService.multi_match_prefix_search")
    def test_search_tags(self, role, mocked_search):
        mocked_search.return_value = self.opensearch_tags_mocked_return(
            tags=self.tags, query=self.query
        )
        user = self.get_parameterized_test_user(role)
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("OrganizationTag-list", args=(self.organization.code,))
            + f"?search={self.query}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), len(self.tags))
        self.assertListEqual(
            [tag["id"] for tag in content],
            [tag.id for tag in self.tags],
        )
        for tag in content:
            for value in tag["highlight"].values():
                self.assertIn(f"<em>{self.query}</em>", value)


class SearchClassificationTagTestCase(WikipediaTestCase, SearchTestCaseMixin):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()

        # Query is title_ because the class that mocks wikipe
        cls.query = faker.word()

        # enabled tag classification
        cls.tag_1 = TagFactory(
            organization=cls.organization,
            title_en=cls.query,
            title_fr="",
            description_en="",
            description_fr="",
        )
        cls.tag_2 = TagFactory(
            organization=cls.organization,
            description_en=cls.query,
            title_en="",
            title_fr="",
            description_fr="",
        )
        cls.tag_3 = TagFactory(
            organization=cls.organization,
            title_fr=cls.query,
            title_en="",
            description_en="",
            description_fr="",
        )
        cls.tag_4 = TagFactory(
            organization=cls.organization,
            description_fr=cls.query,
            title_en="",
            title_fr="",
            description_en="",
        )
        cls.tags = [cls.tag_1, cls.tag_3, cls.tag_2, cls.tag_4]
        cls.tag_classification = TagClassificationFactory(
            organization=cls.organization, tags=cls.tags
        )

        # wikipedia tag classification
        cls.wikipedia_tag_1 = TagFactory(
            type=Tag.TagType.WIKIPEDIA,
            title_en=cls.query,
            title_fr="",
            description_en="",
            description_fr="",
        )
        cls.wikipedia_tag_2 = TagFactory(
            type=Tag.TagType.WIKIPEDIA,
            description_en=cls.query,
            title_en="",
            title_fr="",
            description_fr="",
        )
        cls.wikipedia_tag_3 = TagFactory(
            type=Tag.TagType.WIKIPEDIA,
            title_fr=cls.query,
            title_en="",
            description_en="",
            description_fr="",
        )
        cls.wikipedia_tag_4 = TagFactory(
            type=Tag.TagType.WIKIPEDIA,
            description_fr=cls.query,
            title_en="",
            title_fr="",
            description_en="",
        )
        cls.wikipedia_tags = [
            cls.wikipedia_tag_1,
            cls.wikipedia_tag_3,
            cls.wikipedia_tag_2,
            cls.wikipedia_tag_4,
        ]

        cls.not_returned_wikipedia_tags = [
            TagFactory(type=Tag.TagType.WIKIPEDIA, title_en=str(i))
            for i in range(5, 10)
        ]
        cls.wikipedia_tag_classification = (
            TagClassification.get_or_create_default_classification(
                classification_type=TagClassification.TagClassificationType.WIKIPEDIA,
            )
        )
        cls.wikipedia_tag_classification.tags.add(
            *cls.wikipedia_tags, *cls.not_returned_wikipedia_tags
        )

        # other tag classification
        cls.other_tag = TagFactory(organization=cls.organization, title_en=cls.query)
        TagClassificationFactory(
            organization=cls.organization, tags=[cls.tag_1, cls.other_tag]
        )

        # Enable tag classifications for the organization
        cls.organization.enabled_projects_tag_classifications.set(
            [cls.tag_classification, cls.wikipedia_tag_classification]
        )
        cls.organization.enabled_skills_tag_classifications.set(
            [cls.tag_classification, cls.wikipedia_tag_classification]
        )

        # Expected results
        cls.classifications = {
            "wikipedia": {
                "id": cls.wikipedia_tag_classification.id,
                "tags": cls.wikipedia_tags,
            },
            "classification": {
                "id": cls.tag_classification.id,
                "tags": cls.tags,
            },
            "projects": {
                "id": "enabled-for-projects",
                "tags": cls.tags + cls.wikipedia_tags,
            },
            "skills": {
                "id": "enabled-for-projects",
                "tags": cls.tags + cls.wikipedia_tags,
            },
        }

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, "wikipedia"),
            (TestRoles.DEFAULT, "wikipedia"),
            (TestRoles.ANONYMOUS, "classification"),
            (TestRoles.DEFAULT, "classification"),
            (TestRoles.ANONYMOUS, "projects"),
            (TestRoles.DEFAULT, "projects"),
            (TestRoles.ANONYMOUS, "skills"),
            (TestRoles.DEFAULT, "skills"),
        ]
    )
    @patch("apps.search.interface.OpenSearchService.multi_match_prefix_search")
    @patch("services.wikipedia.interface.WikipediaService.wbgetentities")
    @patch("services.wikipedia.interface.WikipediaService.wbsearchentities")
    def test_search_tags(
        self,
        role,
        classification,
        mocked_wikipedia_search,
        mocked_wikipedia_get,
        mocked_search,
    ):
        user = self.get_parameterized_test_user(role)
        self.client.force_authenticate(user)

        mocked_wikipedia_search.return_value = self.search_wikipedia_tag_mocked_return(
            limit=0,
            offset=10,
            wikipedia_qids=[tag.external_id for tag in self.wikipedia_tags],
        )
        mocked_wikipedia_get.return_value = (
            self.get_existing_wikipedia_tags_mocked_return(tags=self.wikipedia_tags)
        )
        mocked_search.return_value = self.opensearch_tags_mocked_return(
            tags=self.classifications[classification]["tags"], query=self.query
        )

        response = self.client.get(
            reverse(
                "ClassificationTag-list",
                args=(
                    self.organization.code,
                    self.classifications[classification]["id"],
                ),
            )
            + f"?search={self.query}&limit=10&offsef=0"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(
            len(content), len(self.classifications[classification]["tags"])
        )
        self.assertListEqual(
            [tag["id"] for tag in content],
            [tag.id for tag in self.classifications[classification]["tags"]],
        )
        for tag in content:
            for value in tag["highlight"].values():
                self.assertIn(f"<em>{self.query}</em>", value)
