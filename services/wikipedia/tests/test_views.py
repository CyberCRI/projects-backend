from unittest.mock import patch

from django.urls import reverse
from faker import Faker
from rest_framework import status

from apps.commons.test.testcases import JwtAPITestCase, TagTestCaseMixin
from apps.misc.factories import WikipediaTagFactory
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory

faker = Faker()


class SearchWikipediaTagTestCase(JwtAPITestCase, TagTestCaseMixin):
    @patch("services.wikipedia.interface.WikipediaService.wbsearchentities")
    def test_search_tags(self, mocked):
        mocked.side_effect = self.search_wikipedia_tag_mocked_side_effect
        response = self.client.get(
            reverse("WikibaseItem-list") + f"?query={faker.word()}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), 100)
        result = content[0]
        for key in ["wikipedia_qid", "name", "description"]:
            self.assertIn(key, result)

    @patch("services.wikipedia.interface.WikipediaService.wbsearchentities")
    def test_search_tags_pagination(self, mocked):
        mocked.side_effect = self.search_wikipedia_tag_mocked_side_effect
        response = self.client.get(
            reverse("WikibaseItem-list") + f"?query={faker.word()}&limit=10"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertIn("limit=10", content["next"])
        self.assertIn("offset=10", content["next"])
        self.assertEqual(len(content["results"]), 10)


class AutocompleteWikipediaTagTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.query = faker.word()

        cls.organization = OrganizationFactory()

        # Projects to which the tags are attached for ordering
        cls.project_1 = ProjectFactory(organizations=[cls.organization])
        cls.project_2 = ProjectFactory(organizations=[cls.organization])
        cls.project_3 = ProjectFactory(organizations=[cls.organization])
        cls.project_4 = ProjectFactory(organizations=[cls.organization])
        cls.project_5 = ProjectFactory(organizations=[cls.organization])

        # First tags returned by the autocomplete endpoint
        cls.tag_1 = WikipediaTagFactory(name_en=cls.query)
        cls.tag_2 = WikipediaTagFactory(name_en=f"{cls.query} abcd")
        cls.tag_3 = WikipediaTagFactory(name_en=f"{cls.query}_abcd")
        cls.tag_4 = WikipediaTagFactory(name_en=f"{cls.query}abcd")
        cls.tag_5 = WikipediaTagFactory(name_en=f"abcd {cls.query}")

        # Other tags returned by the autocomplete endpoint
        cls.unused_tags = []
        for _ in range(5):
            cls.unused_tags.append(
                WikipediaTagFactory(name_en=cls.query + faker.word())
            )

        # Other tags not returned by the autocomplete endpoint
        not_returned = WikipediaTagFactory(name_en=f"abcd{cls.query}")
        WikipediaTagFactory.create_batch(5)

        # Attach tags to projects
        cls.project_1.wikipedia_tags.add(
            cls.tag_1, cls.tag_2, cls.tag_3, cls.tag_4, cls.tag_5, not_returned
        )
        cls.project_2.wikipedia_tags.add(
            cls.tag_1, cls.tag_2, cls.tag_3, cls.tag_4, not_returned
        )
        cls.project_3.wikipedia_tags.add(cls.tag_1, cls.tag_2, cls.tag_3, not_returned)
        cls.project_4.wikipedia_tags.add(cls.tag_1, cls.tag_2, not_returned)
        cls.project_5.wikipedia_tags.add(cls.tag_1, not_returned)

    def test_autocomplete_default_limit(self):
        response = self.client.get(
            reverse("WikibaseItem-autocomplete") + f"?query={self.query}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(len(content), 5)
        self.assertListEqual(
            content,
            [
                self.tag_1.name,
                self.tag_2.name,
                self.tag_3.name,
                self.tag_4.name,
                self.tag_5.name,
            ],
        )

    def test_autocomplete_custom_limit(self):
        response = self.client.get(
            reverse("WikibaseItem-autocomplete") + f"?query={self.query}&limit=10"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(len(content), 10)
        self.assertListEqual(
            content[:5],
            [
                self.tag_1.name,
                self.tag_2.name,
                self.tag_3.name,
                self.tag_4.name,
                self.tag_5.name,
            ],
        )
        self.assertSetEqual(set(content[5:]), {tag.name for tag in self.unused_tags})
