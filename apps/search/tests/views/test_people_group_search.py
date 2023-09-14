import time

from algoliasearch_django import algolia_engine
from django.urls import reverse

from apps.accounts.factories import PeopleGroupFactory, UserFactory
from apps.accounts.models import PeopleGroup, ProjectUser
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase
from apps.commons.test.mixins import skipUnlessAlgolia
from apps.organizations.factories import OrganizationFactory


@skipUnlessAlgolia
class PeopleGroupSearchTestCase(JwtAPITestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.organization = OrganizationFactory()
        PeopleGroup.objects.all().delete()  # Delete people_groups created by the factories
        cls.public_people_group = PeopleGroupFactory(
            name="algolia",
            publication_status=PeopleGroup.PublicationStatus.PUBLIC,
            organization=cls.organization,
            type="club",
            sdgs=[2],
        )
        cls.organization_2 = OrganizationFactory()
        cls.public_people_group_2 = PeopleGroupFactory(
            name="algolia",
            publication_status=PeopleGroup.PublicationStatus.PUBLIC,
            organization=cls.organization_2,
            sdgs=[1],
            type="group",
        )
        cls.private_people_group = PeopleGroupFactory(
            name="algolia",
            publication_status=PeopleGroup.PublicationStatus.PRIVATE,
            organization=cls.organization,
            type="club",
            sdgs=[2],
        )
        cls.org_people_group = PeopleGroupFactory(
            name="algolia",
            publication_status=PeopleGroup.PublicationStatus.ORG,
            organization=cls.organization,
            type="club",
            sdgs=[2],
        )
        cls.member_people_group = PeopleGroupFactory(
            name="algolia",
            publication_status=PeopleGroup.PublicationStatus.PRIVATE,
            organization=cls.organization,
            type="club",
            sdgs=[2],
        )
        ProjectUser.objects.all().delete()  # Delete users created by the factories
        cls.member = UserFactory()
        cls.member_people_group.members.add(cls.member)
        algolia_engine.reindex_all(PeopleGroup)
        time.sleep(10)  # reindexing is asynchronous, wait for it to finish

    def test_search_people_group_anonymous(self):
        response = self.client.get(
            reverse("PeopleGroupSearch-search", args=("algolia",))
        )
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 2)
        self.assertEqual(
            {people_group["id"] for people_group in content},
            {self.public_people_group.id, self.public_people_group_2.id},
        )

    def test_search_people_group_authenticated(self):
        user = UserFactory()
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("PeopleGroupSearch-search", args=("algolia",))
        )
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 2)
        self.assertEqual(
            {people_group["id"] for people_group in content},
            {self.public_people_group.id, self.public_people_group_2.id},
        )

    def test_search_people_group_org_user(self):
        user = UserFactory()
        self.organization.users.add(user)
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("PeopleGroupSearch-search", args=("algolia",))
        )
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 3)
        self.assertEqual(
            {people_group["id"] for people_group in content},
            {
                self.public_people_group.id,
                self.public_people_group_2.id,
                self.org_people_group.id,
            },
        )

    def test_search_people_group_org_facilitator(self):
        user = UserFactory()
        self.organization.facilitators.add(user)
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("PeopleGroupSearch-search", args=("algolia",))
        )
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 5)
        self.assertEqual(
            {people_group["id"] for people_group in content},
            {
                self.public_people_group.id,
                self.public_people_group_2.id,
                self.org_people_group.id,
                self.private_people_group.id,
                self.member_people_group.id,
            },
        )

    def test_search_people_group_org_admin(self):
        user = UserFactory()
        self.organization.admins.add(user)
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("PeopleGroupSearch-search", args=("algolia",))
        )
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 5)
        self.assertEqual(
            {people_group["id"] for people_group in content},
            {
                self.public_people_group.id,
                self.public_people_group_2.id,
                self.org_people_group.id,
                self.private_people_group.id,
                self.member_people_group.id,
            },
        )

    def test_search_people_group_superadmin(self):
        user = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("PeopleGroupSearch-search", args=("algolia",))
        )
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 5)
        self.assertEqual(
            {people_group["id"] for people_group in content},
            {
                self.public_people_group.id,
                self.public_people_group_2.id,
                self.org_people_group.id,
                self.private_people_group.id,
                self.member_people_group.id,
            },
        )

    def test_search_people_group_member(self):
        self.client.force_authenticate(self.member)
        response = self.client.get(
            reverse("PeopleGroupSearch-search", args=("algolia",))
        )
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 3)
        self.assertEqual(
            {people_group["id"] for people_group in content},
            {
                self.public_people_group.id,
                self.public_people_group_2.id,
                self.member_people_group.id,
            },
        )

    def test_filter_by_organization(self):
        user = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("PeopleGroupSearch-search", args=("algolia",))
            + f"?organizations={self.organization_2.code}"
        )
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 1)
        self.assertEqual(
            {people_group["id"] for people_group in content},
            {self.public_people_group_2.id},
        )

    def test_filter_by_sdgs(self):
        user = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("PeopleGroupSearch-search", args=("algolia",)) + "?sdgs=1"
        )
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 1)
        self.assertEqual(
            {people_group["id"] for people_group in content},
            {self.public_people_group_2.id},
        )

    def test_filter_by_type(self):
        user = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("PeopleGroupSearch-search", args=("algolia",)) + "?types=group"
        )
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 1)
        self.assertEqual(
            {people_group["id"] for people_group in content},
            {self.public_people_group_2.id},
        )
