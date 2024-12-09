from typing import Any, Dict, Union

from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from apps.accounts.factories import PeopleGroupFactory, UserFactory
from apps.accounts.models import PeopleGroup, PrivacySettings
from apps.commons.test import JwtAPITestCase, skipUnlessSearch
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory
from apps.projects.models import Project
from apps.search.models import SearchObject


@skipUnlessSearch
class MixedSearchTestCase(JwtAPITestCase):
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
        Project.objects.filter(pk=cls.project_2.pk).update(
            updated_at=timezone.localtime(timezone.now() - timezone.timedelta(days=4))
        )
        PeopleGroup.objects.filter(pk=cls.people_group_1.pk).update(
            updated_at=timezone.localtime(timezone.now() - timezone.timedelta(days=5))
        )
        PeopleGroup.objects.filter(pk=cls.people_group_2.pk).update(
            updated_at=timezone.localtime(timezone.now() - timezone.timedelta(days=1))
        )
        # Index the data
        call_command("opensearch", "index", "rebuild", "--force")
        call_command("opensearch", "document", "index", "--force", "--refresh")

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
