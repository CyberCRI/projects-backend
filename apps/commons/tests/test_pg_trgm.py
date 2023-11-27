from django.urls import reverse

from apps.accounts.factories import PeopleGroupFactory, UserFactory
from apps.accounts.models import PeopleGroup
from apps.commons.test import JwtAPITestCase
from apps.misc.factories import TagFactory, WikipediaTagFactory


class PostgresTrigramTestCase(JwtAPITestCase):
    def test_user_search_pg_trgm(self):
        user = UserFactory(given_name="ééé", family_name="abcdef", email="", job="")
        UserFactory(given_name="aee", family_name="abcxyz", email="", job="")
        for query in ["abcdef", "abcdea", "ééé", "èèè", "eee"]:
            response = self.client.get(
                reverse("ProjectUser-list") + f"?search={query}",
            )
            assert response.status_code == 200
            content = response.json()["results"]
            assert len(content) >= 1
            assert content[0]["keycloak_id"] == user.keycloak_id

    def test_people_group_search_pg_trgrm(self):
        people_group = PeopleGroupFactory(
            name="ééé abcdef", publication_status=PeopleGroup.PublicationStatus.PUBLIC
        )
        organization = people_group.organization
        PeopleGroupFactory(
            name="aee abcxyz",
            publication_status=PeopleGroup.PublicationStatus.PUBLIC,
            organization=organization,
        )

        for query in ["abcdef", "abcdea", "ééé", "èèè", "eee"]:
            response = self.client.get(
                reverse("PeopleGroup-list", args=(organization.code,))
                + f"?search={query}",
            )
            assert response.status_code == 200
            content = response.json()["results"]
            assert len(content) >= 1
            assert content[0]["id"] == people_group.id

    def test_wikipedia_tag_search_pg_trgrm(self):
        wikipedia_tag = WikipediaTagFactory(name_en="abcdef", name_fr="ééé")
        WikipediaTagFactory(name_en="abcxyz", name_fr="aee")
        for query in ["abcdef", "abcdea", "ééé", "èèè", "eee"]:
            response = self.client.get(
                reverse("WikipediaTag-list") + f"?search={query}",
            )
            assert response.status_code == 200
            content = response.json()["results"]
            assert len(content) >= 1
            assert content[0]["wikipedia_qid"] == wikipedia_tag.wikipedia_qid

    def test_tag_search_pg_trgrm(self):
        tag = TagFactory(name="ééé abcdef")
        TagFactory(name="aee abcxyz")
        for query in ["abcdef", "abcdea", "ééé", "èèè", "eee"]:
            response = self.client.get(
                reverse("Tag-list") + f"?search={query}",
            )
            assert response.status_code == 200
            content = response.json()["results"]
            assert len(content) >= 1
            assert content[0]["id"] == tag.id