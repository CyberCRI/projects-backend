from typing import Any, Dict, Union
from unittest.mock import patch

from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from apps.accounts.factories import PeopleGroupFactory, UserFactory
from apps.accounts.models import PeopleGroup, PrivacySettings
from apps.commons.test import JwtAPITestCase
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory
from apps.projects.models import Project
from apps.search.models import SearchObject
from apps.search.testcases import SearchTestCaseMixin


class MixedSearchTestCase(JwtAPITestCase, SearchTestCaseMixin):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.people_group_1 = PeopleGroupFactory(
            name="opensearch",
            publication_status=PeopleGroup.PublicationStatus.PUBLIC,
            organization=cls.organization,
        )
        cls.people_group_2 = PeopleGroupFactory(
            name="opensearch",
            publication_status=PeopleGroup.PublicationStatus.PUBLIC,
            organization=cls.organization,
        )
        cls.user_1 = UserFactory(
            given_name="opensearch",
            family_name="",
            publication_status=PrivacySettings.PrivacyChoices.PUBLIC,
            groups=[cls.organization.get_users()],
            last_login=timezone.localtime(timezone.now() - timezone.timedelta(days=3)),
        )
        cls.user_2 = UserFactory(
            given_name="opensearch",
            family_name="",
            publication_status=PrivacySettings.PrivacyChoices.PUBLIC,
            groups=[cls.organization.get_users()],
            last_login=timezone.localtime(timezone.now() - timezone.timedelta(days=2)),
        )
        cls.project_1 = ProjectFactory(
            title="opensearch",
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[cls.organization],
        )
        cls.project_2 = ProjectFactory(
            title="opensearch",
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[cls.organization],
        )
        Project.objects.filter(pk=cls.project_1.pk).update(
            updated_at=timezone.localtime(timezone.now())
        )
        cls.project_1.refresh_from_db()
        Project.objects.filter(pk=cls.project_2.pk).update(
            updated_at=timezone.localtime(timezone.now() - timezone.timedelta(days=4))
        )
        cls.project_2.refresh_from_db()
        PeopleGroup.objects.filter(pk=cls.people_group_1.pk).update(
            updated_at=timezone.localtime(timezone.now() - timezone.timedelta(days=5))
        )
        cls.people_group_1.refresh_from_db()
        PeopleGroup.objects.filter(pk=cls.people_group_2.pk).update(
            updated_at=timezone.localtime(timezone.now() - timezone.timedelta(days=1))
        )
        cls.people_group_2.refresh_from_db()

        search_objects = (
            [
                SearchObject(
                    type=SearchObject.SearchObjectType.PEOPLE_GROUP,
                    people_group=people_group,
                    last_update=people_group.updated_at,
                )
                for people_group in [cls.people_group_1, cls.people_group_2]
            ]
            + [
                SearchObject(
                    type=SearchObject.SearchObjectType.USER,
                    user=user,
                    last_update=user.last_login if user.last_login else None,
                )
                for user in [cls.user_1, cls.user_2]
            ]
            + [
                SearchObject(
                    type=SearchObject.SearchObjectType.PROJECT,
                    project=project,
                    last_update=project.updated_at,
                )
                for project in [cls.project_1, cls.project_2]
            ]
        )
        cls.search_objects = SearchObject.objects.bulk_create(search_objects)

    @staticmethod
    def get_object_id_from_search_object(
        search_object: Dict[str, Any],
    ) -> Union[int, str, None]:
        if search_object["type"] == SearchObject.SearchObjectType.PEOPLE_GROUP:
            return search_object["people_group"]["id"]
        if search_object["type"] == SearchObject.SearchObjectType.PROJECT:
            return search_object["project"]["id"]
        if search_object["type"] == SearchObject.SearchObjectType.USER:
            return search_object["user"]["id"]
        return None

    @patch("apps.search.interface.OpenSearchService.multi_match_search")
    def test_search_mixed_index(self, mocked_search):
        mocked_search.return_value = self.opensearch_search_objects_mocked_return(
            search_objects=self.search_objects,
            query="opensearch",
        )
        response = self.client.get(
            reverse("Search-search", args=("opensearch",))
            + f"?organizations={self.organization.code}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), 6)
        self.assertSetEqual(
            {
                (
                    search_object["type"],
                    self.get_object_id_from_search_object(search_object),
                )
                for search_object in content
            },
            {
                (SearchObject.SearchObjectType.PROJECT, self.project_1.pk),
                (SearchObject.SearchObjectType.PEOPLE_GROUP, self.people_group_2.pk),
                (SearchObject.SearchObjectType.USER, self.user_2.pk),
                (SearchObject.SearchObjectType.USER, self.user_1.pk),
                (SearchObject.SearchObjectType.PROJECT, self.project_2.pk),
                (SearchObject.SearchObjectType.PEOPLE_GROUP, self.people_group_1.pk),
            },
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
