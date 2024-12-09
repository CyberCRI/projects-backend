from django.core.management import call_command
from django.urls import reverse
from parameterized import parameterized
from rest_framework import status

from apps.accounts.factories import PeopleGroupFactory, UserFactory
from apps.accounts.models import PeopleGroup, ProjectUser
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase, TestRoles, skipUnlessSearch
from apps.organizations.factories import OrganizationFactory
from apps.search.models import SearchObject


@skipUnlessSearch
class PeopleGroupSearchTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        PeopleGroup.objects.all().delete()  # Delete people_groups created by the factories
        cls.public_people_group_1 = PeopleGroupFactory(
            name="opensearch",
            publication_status=PeopleGroup.PublicationStatus.PUBLIC,
            organization=cls.organization,
            sdgs=[2],
        )
        cls.organization_2 = OrganizationFactory()
        cls.public_people_group_2 = PeopleGroupFactory(
            name="opensearch",
            publication_status=PeopleGroup.PublicationStatus.PUBLIC,
            organization=cls.organization_2,
            sdgs=[1],
        )
        cls.private_people_group = PeopleGroupFactory(
            name="opensearch",
            publication_status=PeopleGroup.PublicationStatus.PRIVATE,
            organization=cls.organization,
            sdgs=[2],
        )
        cls.org_people_group = PeopleGroupFactory(
            name="opensearch",
            publication_status=PeopleGroup.PublicationStatus.ORG,
            organization=cls.organization,
            sdgs=[2],
        )
        cls.member_people_group = PeopleGroupFactory(
            name="opensearch",
            publication_status=PeopleGroup.PublicationStatus.PRIVATE,
            organization=cls.organization,
            sdgs=[2],
        )
        ProjectUser.objects.all().delete()  # Delete users created by the factories
        cls.superadmin = UserFactory(groups=[get_superadmins_group()])
        cls.member = UserFactory()
        cls.member_people_group.members.add(cls.member)
        cls.groups = {
            "public_1": cls.public_people_group_1,
            "public_2": cls.public_people_group_2,
            "private": cls.private_people_group,
            "org": cls.org_people_group,
            "member": cls.member_people_group,
        }
        # Index the data
        call_command("opensearch", "index", "rebuild", "--force")
        call_command("opensearch", "document", "index", "--force", "--refresh")

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, ("public_1", "public_2")),
            (TestRoles.DEFAULT, ("public_1", "public_2")),
            (
                TestRoles.SUPERADMIN,
                ("public_1", "public_2", "private", "org", "member"),
            ),
            (TestRoles.ORG_ADMIN, ("public_1", "public_2", "private", "org", "member")),
            (
                TestRoles.ORG_FACILITATOR,
                ("public_1", "public_2", "private", "org", "member"),
            ),
            (TestRoles.ORG_USER, ("public_1", "public_2", "org")),
            (TestRoles.GROUP_MEMBER, ("public_1", "public_2", "member")),
        ]
    )
    def test_search_people_group(self, role, retrieved_groups):
        user = self.get_parameterized_test_user(
            role, instances=[self.member_people_group]
        )
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("Search-search", args=("opensearch",)) + "?types=people_group"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), len(retrieved_groups))
        self.assertEqual(
            {group["type"] for group in content},
            {SearchObject.SearchObjectType.PEOPLE_GROUP for _ in retrieved_groups},
        )
        self.assertSetEqual(
            {group["people_group"]["id"] for group in content},
            {self.groups[group].id for group in retrieved_groups},
        )

    def test_filter_by_organization(self):
        self.client.force_authenticate(self.superadmin)
        response = self.client.get(
            reverse("Search-search", args=("opensearch",))
            + "?types=people_group"
            + f"&organizations={self.organization_2.code}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), 1)
        self.assertEqual(
            {group["type"] for group in content},
            {SearchObject.SearchObjectType.PEOPLE_GROUP},
        )
        self.assertSetEqual(
            {group["people_group"]["id"] for group in content},
            {self.public_people_group_2.id},
        )

    def test_filter_by_sdgs(self):
        self.client.force_authenticate(self.superadmin)
        response = self.client.get(
            reverse("Search-search", args=("opensearch",))
            + "?types=people_group"
            + "&sdgs=1"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), 1)
        self.assertEqual(
            {group["type"] for group in content},
            {SearchObject.SearchObjectType.PEOPLE_GROUP},
        )
        self.assertSetEqual(
            {group["people_group"]["id"] for group in content},
            {self.public_people_group_2.id},
        )
