import time
from typing import Any, Dict, Union

from algoliasearch_django import algolia_engine
from django.urls import reverse
from rest_framework import status

from apps.accounts.factories import PeopleGroupFactory, UserFactory
from apps.accounts.models import PeopleGroup, PrivacySettings
from apps.commons.test import JwtAPITestCase, skipUnlessAlgolia
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory
from apps.projects.models import Project
from apps.search.models import SearchObject
from apps.search.tasks import (
    update_or_create_people_group_search_object_task,
    update_or_create_project_search_object_task,
    update_or_create_user_search_object_task,
)


@skipUnlessAlgolia
class PeopleGroupSearchTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.people_group_1 = PeopleGroupFactory(
            name="algolia",
            publication_status=PeopleGroup.PublicationStatus.PUBLIC,
            organization=cls.organization,
        )
        cls.people_group_2 = PeopleGroupFactory(
            name="algolia",
            publication_status=PeopleGroup.PublicationStatus.PUBLIC,
            organization=cls.organization,
        )
        cls.user_1 = UserFactory(
            given_name="algolia",
            family_name="",
            publication_status=PrivacySettings.PrivacyChoices.PUBLIC,
            groups=[cls.organization.get_users()],
        )
        cls.user_2 = UserFactory(
            given_name="algolia",
            family_name="",
            publication_status=PrivacySettings.PrivacyChoices.PUBLIC,
            groups=[cls.organization.get_users()],
        )
        cls.project_1 = ProjectFactory(
            title="algolia",
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[cls.organization],
        )
        cls.project_2 = ProjectFactory(
            title="algolia",
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[cls.organization],
        )
        # Create search objects manually in a fixed order to test sorting
        update_or_create_people_group_search_object_task(cls.people_group_1.pk)
        update_or_create_project_search_object_task(cls.project_2.pk)
        update_or_create_user_search_object_task(cls.user_1.pk)
        update_or_create_user_search_object_task(cls.user_2.pk)
        update_or_create_people_group_search_object_task(cls.people_group_2.pk)
        update_or_create_project_search_object_task(cls.project_1.pk)
        algolia_engine.reindex_all(SearchObject)
        time.sleep(10)  # reindexing is asynchronous, wait for it to finish

    @staticmethod
    def get_object_id_from_search_object(
        search_object: Dict[str, Any]
    ) -> Union[int, str, None]:
        if search_object["type"] == SearchObject.SearchObjectType.PEOPLE_GROUP:
            return search_object["people_group"]["id"]
        if search_object["type"] == SearchObject.SearchObjectType.PROJECT:
            return search_object["project"]["id"]
        if search_object["type"] == SearchObject.SearchObjectType.USER:
            return search_object["user"]["id"]
        return None

    def test_search_mixed_index(self):
        response = self.client.get(
            reverse("Search-search", args=("algolia",))
            + f"?organizations={self.organization.code}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), 6)
        self.assertListEqual(
            [
                (
                    search_object["type"],
                    self.get_object_id_from_search_object(search_object),
                )
                for search_object in content
            ],
            [
                (SearchObject.SearchObjectType.PROJECT, self.project_1.pk),
                (SearchObject.SearchObjectType.PEOPLE_GROUP, self.people_group_2.pk),
                (SearchObject.SearchObjectType.USER, self.user_2.pk),
                (SearchObject.SearchObjectType.USER, self.user_1.pk),
                (SearchObject.SearchObjectType.PROJECT, self.project_2.pk),
                (SearchObject.SearchObjectType.PEOPLE_GROUP, self.people_group_1.pk),
            ],
        )

    def test_search_mixed_index_no_query(self):
        response = self.client.get(
            reverse("Search-list") + f"?organizations={self.organization.code}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), 6)
        self.assertListEqual(
            [
                (
                    search_object["type"],
                    self.get_object_id_from_search_object(search_object),
                )
                for search_object in content
            ],
            [
                (SearchObject.SearchObjectType.PROJECT, self.project_1.pk),
                (SearchObject.SearchObjectType.PEOPLE_GROUP, self.people_group_2.pk),
                (SearchObject.SearchObjectType.USER, self.user_2.pk),
                (SearchObject.SearchObjectType.USER, self.user_1.pk),
                (SearchObject.SearchObjectType.PROJECT, self.project_2.pk),
                (SearchObject.SearchObjectType.PEOPLE_GROUP, self.people_group_1.pk),
            ],
        )
