from contextlib import suppress

from django.conf import settings
from django.core.management import call_command
from faker import Faker
from parameterized import parameterized

from apps.accounts.factories import PeopleGroupFactory, UserFactory
from apps.commons.test import JwtAPITestCase, skipUnlessSearch
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory
from apps.search.interface import OpenSearchService
from apps.skills.factories import TagFactory

faker = Faker()


@skipUnlessSearch
class OpenSearchServiceTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()

        cls.query = faker.password(length=40, special_chars=False)
        cls.query_2 = faker.password(length=40, special_chars=False)

        cls.project = ProjectFactory(
            organizations=[cls.organization], title=cls.query, description=cls.query_2
        )
        cls.people_group = PeopleGroupFactory(
            organization=cls.organization, name=cls.query, description=cls.query_2
        )
        cls.user = UserFactory(given_name=cls.query, family_name=cls.query_2)
        cls.tag = TagFactory(
            organization=cls.organization,
            title_en=cls.query,
            description_en=cls.query_2,
        )

        # Other objects that should come first in multi_match search
        cls.project_2 = ProjectFactory(
            organizations=[cls.organization], title=cls.query_2
        )
        cls.people_group_2 = PeopleGroupFactory(
            organization=cls.organization, name=cls.query_2
        )
        cls.user_2 = UserFactory(given_name=cls.query_2)
        cls.tag_2 = TagFactory(organization=cls.organization, title_fr=cls.query_2)

        ProjectFactory(organizations=[cls.organization])
        PeopleGroupFactory(organization=cls.organization)
        UserFactory()
        TagFactory(organization=cls.organization)

        cls.results = {
            "project": cls.project,
            "people_group": cls.people_group,
            "user": cls.user,
            "tag": cls.tag,
            "project_2": cls.project_2,
            "people_group_2": cls.people_group_2,
            "user_2": cls.user_2,
            "tag_2": cls.tag_2,
        }
        with suppress(SystemExit):
            call_command("opensearch", "index", "rebuild", "--force", "--ignore-error")
        with suppress(SystemExit):
            call_command("opensearch", "document", "index", "--force", "--refresh")

    @parameterized.expand(
        [
            ("project", ["title^2", "content^1"], ["project_2", "project"]),
            (
                "people_group",
                ["name^2", "content^1"],
                ["people_group_2", "people_group"],
            ),
            ("tag", ["title^2", "content^1"], ["tag_2", "tag"]),
            ("user", ["given_name^2", "family_name^1"], ["user_2", "user"]),
        ]
    )
    def test_multi_match_search(self, index, fields, expected_results):
        indices = [
            f"{settings.OPENSEARCH_INDEX_PREFIX}-{index}",
        ]
        response = OpenSearchService.multi_match_search(
            indices=indices, query=self.query_2, fields=fields
        )
        hits = response.hits
        self.assertEqual(len(hits), len(expected_results))
        self.assertListEqual(
            [hit.id for hit in hits],
            [self.results[result].id for result in expected_results],
        )

    @parameterized.expand(
        [
            ("project", ["title"], ["project"]),
            ("people_group", ["name"], ["people_group"]),
            ("tag", ["title"], ["tag"]),
            ("user", ["given_name"], ["user"]),
        ]
    )
    def test_multi_match_search_highlight(self, index, highlight, expected_results):
        indices = f"{settings.OPENSEARCH_INDEX_PREFIX}-{index}"
        response = OpenSearchService.multi_match_search(
            indices=indices, query=self.query, fields=highlight, highlight=highlight
        )
        hits = response.hits
        self.assertEqual(len(hits), len(expected_results))
        for hit in hits:
            returned_highlight = hit.meta.highlight.to_dict()
            for field in highlight:
                self.assertIn(field, returned_highlight)
                self.assertTrue(
                    any(
                        f"<em>{self.query}</em>" in highlight
                        for highlight in returned_highlight[field]
                    )
                )

    def test_multi_match_search_multiple_indices(self):
        indices = [
            f"{settings.OPENSEARCH_INDEX_PREFIX}-tag",
        ]
        response = OpenSearchService.multi_match_search(
            indices=indices,
            query=self.query_2,
            fields=["title^2", "content^1"],
        )
        hits = response.hits
        self.assertEqual(len(hits), 2)
        self.assertSetEqual(
            {hit.id for hit in hits},
            {self.tag_2.id, self.tag.id},
        )

    def test_multi_match_search_pagination(self):
        indices = [
            f"{settings.OPENSEARCH_INDEX_PREFIX}-tag",
        ]
        response = OpenSearchService.multi_match_search(
            indices=indices,
            query=self.query_2,
            fields=["title^2", "content^1"],
            limit=1,
            offset=0,
        )
        hits = response.hits
        self.assertEqual(len(hits), 1)
        hit_1 = hits[0]
        self.assertEqual(hit_1.id, self.tag_2.id)

        response = OpenSearchService.multi_match_search(
            indices=indices,
            query=self.query_2,
            fields=["title^2", "content^1"],
            limit=1,
            offset=1,
        )
        hits = response.hits
        self.assertEqual(len(hits), 1)
        hit_2 = hits[0]
        self.assertEqual(hit_2.id, self.tag.id)
