from django.urls import reverse

from apps.accounts.factories import UserFactory
from apps.commons.test import JwtAPITestCase


class PostgresTrigramTestCase(JwtAPITestCase):
    def test_user_search_pg_trgm(self):
        user = UserFactory(given_name="ééé", family_name="abcdef", email="", job="")
        for query in ["abcdef", "xbcdef", "ééé", "èèè", "eee"]:
            response = self.client.get(
                reverse("ProjectUser-list") + f"?search={query}",
            )
            assert response.status_code == 200
            content = response.json()["results"]
            assert len(content) == 1
            assert content[0]["keycloak_id"] == user.keycloak_id

    def test_people_group_search_pg_trgrm(self):
        pass

    def test_wikipedia_tag_search_pg_trgrm(self):
        pass

    def test_tag_search_pg_trgrm(self):
        pass
