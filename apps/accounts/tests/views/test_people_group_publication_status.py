from django.urls import reverse

from apps.accounts.factories import PeopleGroupFactory, UserFactory
from apps.accounts.models import PeopleGroup, ProjectUser
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase
from apps.organizations.factories import OrganizationFactory


class PeopleGroupPublicationStatusTestCase(JwtAPITestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.organization = OrganizationFactory()
        PeopleGroup.objects.all().delete()  # Delete people_groups created by the factories
        cls.public_group = PeopleGroupFactory(
            publication_status=PeopleGroup.PublicationStatus.PUBLIC,
            organization=cls.organization,
        )
        cls.private_group = PeopleGroupFactory(
            publication_status=PeopleGroup.PublicationStatus.PRIVATE,
            organization=cls.organization,
        )
        cls.org_group = PeopleGroupFactory(
            publication_status=PeopleGroup.PublicationStatus.ORG,
            organization=cls.organization,
        )
        cls.member_group = PeopleGroupFactory(
            publication_status=PeopleGroup.PublicationStatus.PRIVATE,
            organization=cls.organization,
        )
        ProjectUser.objects.all().delete()  # Delete users created by the factories
        cls.member = UserFactory()
        cls.member_group.members.add(cls.member)


class AnonymousUserTestCase(PeopleGroupPublicationStatusTestCase):
    def test_retrieve_people_groups(self):
        for people_group in [
            self.public_group,
            self.private_group,
            self.org_group,
            self.member_group,
        ]:
            response = self.client.get(
                reverse(
                    "PeopleGroup-detail",
                    args=(
                        self.organization.code,
                        people_group.id,
                    ),
                )
            )
            member_response = self.client.get(
                reverse(
                    "PeopleGroup-member",
                    args=(
                        self.organization.code,
                        people_group.id,
                    ),
                )
            )
            project_response = self.client.get(
                reverse(
                    "PeopleGroup-project",
                    args=(
                        self.organization.code,
                        people_group.id,
                    ),
                )
            )
            if people_group == self.public_group:
                self.assertEqual(response.status_code, 200)
                self.assertEqual(member_response.status_code, 200)
                self.assertEqual(project_response.status_code, 200)
            else:
                self.assertEqual(response.status_code, 404)
                self.assertEqual(member_response.status_code, 404)
                self.assertEqual(project_response.status_code, 404)

    def test_list_people_groups(self):
        response = self.client.get(
            reverse("PeopleGroup-list", args=(self.organization.code,))
        )
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 1)
        self.assertEqual(
            {people_group["id"] for people_group in content}, {self.public_group.id}
        )


class AuthenticatedUserTestCase(PeopleGroupPublicationStatusTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = UserFactory()

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.user)

    def test_retrieve_people_groups(self):
        for people_group in [
            self.public_group,
            self.private_group,
            self.org_group,
            self.member_group,
        ]:
            response = self.client.get(
                reverse(
                    "PeopleGroup-detail",
                    args=(
                        self.organization.code,
                        people_group.id,
                    ),
                )
            )
            member_response = self.client.get(
                reverse(
                    "PeopleGroup-member",
                    args=(
                        self.organization.code,
                        people_group.id,
                    ),
                )
            )
            project_response = self.client.get(
                reverse(
                    "PeopleGroup-project",
                    args=(
                        self.organization.code,
                        people_group.id,
                    ),
                )
            )
            if people_group == self.public_group:
                self.assertEqual(response.status_code, 200)
                self.assertEqual(member_response.status_code, 200)
                self.assertEqual(project_response.status_code, 200)
            else:
                self.assertEqual(response.status_code, 404)
                self.assertEqual(member_response.status_code, 404)
                self.assertEqual(project_response.status_code, 404)

    def test_list_people_groups(self):
        response = self.client.get(
            reverse("PeopleGroup-list", args=(self.organization.code,))
        )
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 1)
        self.assertEqual(
            {people_group["id"] for people_group in content}, {self.public_group.id}
        )


class OrganizationMemberTestCase(PeopleGroupPublicationStatusTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = UserFactory()
        cls.organization.users.add(cls.user)

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.user)

    def test_retrieve_people_groups(self):
        for people_group in [
            self.public_group,
            self.private_group,
            self.org_group,
            self.member_group,
        ]:
            response = self.client.get(
                reverse(
                    "PeopleGroup-detail",
                    args=(
                        self.organization.code,
                        people_group.id,
                    ),
                )
            )
            member_response = self.client.get(
                reverse(
                    "PeopleGroup-member",
                    args=(
                        self.organization.code,
                        people_group.id,
                    ),
                )
            )
            project_response = self.client.get(
                reverse(
                    "PeopleGroup-project",
                    args=(
                        self.organization.code,
                        people_group.id,
                    ),
                )
            )
            if people_group in [self.public_group, self.org_group]:
                self.assertEqual(response.status_code, 200)
                self.assertEqual(member_response.status_code, 200)
                self.assertEqual(project_response.status_code, 200)
            else:
                self.assertEqual(response.status_code, 404)
                self.assertEqual(member_response.status_code, 404)
                self.assertEqual(project_response.status_code, 404)

    def test_list_people_groups(self):
        response = self.client.get(
            reverse("PeopleGroup-list", args=(self.organization.code,))
        )
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 3)
        self.assertEqual(
            {people_group["id"] for people_group in content},
            {
                self.organization.get_or_create_root_people_group().id,
                self.public_group.id,
                self.org_group.id,
            },
        )


class OrganizationFacilitatorTestCase(PeopleGroupPublicationStatusTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = UserFactory()
        cls.organization.facilitators.add(cls.user)

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.user)

    def test_retrieve_people_groups(self):
        for people_group in [
            self.public_group,
            self.private_group,
            self.org_group,
            self.member_group,
        ]:
            response = self.client.get(
                reverse(
                    "PeopleGroup-detail",
                    args=(
                        self.organization.code,
                        people_group.id,
                    ),
                )
            )
            member_response = self.client.get(
                reverse(
                    "PeopleGroup-member",
                    args=(
                        self.organization.code,
                        people_group.id,
                    ),
                )
            )
            project_response = self.client.get(
                reverse(
                    "PeopleGroup-project",
                    args=(
                        self.organization.code,
                        people_group.id,
                    ),
                )
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(member_response.status_code, 200)
            self.assertEqual(project_response.status_code, 200)

    def test_list_people_groups(self):
        response = self.client.get(
            reverse("PeopleGroup-list", args=(self.organization.code,))
        )
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 5)
        self.assertEqual(
            {people_group["id"] for people_group in content},
            {
                self.organization.get_or_create_root_people_group().id,
                self.public_group.id,
                self.org_group.id,
                self.private_group.id,
                self.member_group.id,
            },
        )


class OrganizationAdminTestCase(PeopleGroupPublicationStatusTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = UserFactory()
        cls.organization.admins.add(cls.user)

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.user)

    def test_retrieve_people_groups(self):
        for people_group in [
            self.public_group,
            self.private_group,
            self.org_group,
            self.member_group,
        ]:
            response = self.client.get(
                reverse(
                    "PeopleGroup-detail",
                    args=(
                        self.organization.code,
                        people_group.id,
                    ),
                )
            )
            member_response = self.client.get(
                reverse(
                    "PeopleGroup-member",
                    args=(
                        self.organization.code,
                        people_group.id,
                    ),
                )
            )
            project_response = self.client.get(
                reverse(
                    "PeopleGroup-project",
                    args=(
                        self.organization.code,
                        people_group.id,
                    ),
                )
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(member_response.status_code, 200)
            self.assertEqual(project_response.status_code, 200)

    def test_list_people_groups(self):
        response = self.client.get(
            reverse("PeopleGroup-list", args=(self.organization.code,))
        )
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 5)
        self.assertEqual(
            {people_group["id"] for people_group in content},
            {
                self.organization.get_or_create_root_people_group().id,
                self.public_group.id,
                self.org_group.id,
                self.private_group.id,
                self.member_group.id,
            },
        )


class SuperAdminTestCase(PeopleGroupPublicationStatusTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = UserFactory(
            groups=[get_superadmins_group()],
        )

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.user)

    def test_retrieve_people_groups(self):
        for people_group in [
            self.public_group,
            self.private_group,
            self.org_group,
            self.member_group,
        ]:
            response = self.client.get(
                reverse(
                    "PeopleGroup-detail",
                    args=(
                        self.organization.code,
                        people_group.id,
                    ),
                )
            )
            member_response = self.client.get(
                reverse(
                    "PeopleGroup-member",
                    args=(
                        self.organization.code,
                        people_group.id,
                    ),
                )
            )
            project_response = self.client.get(
                reverse(
                    "PeopleGroup-project",
                    args=(
                        self.organization.code,
                        people_group.id,
                    ),
                )
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(member_response.status_code, 200)
            self.assertEqual(project_response.status_code, 200)

    def test_list_people_groups(self):
        response = self.client.get(
            reverse("PeopleGroup-list", args=(self.organization.code,))
        )
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 5)
        self.assertEqual(
            {people_group["id"] for people_group in content},
            {
                self.organization.get_or_create_root_people_group().id,
                self.public_group.id,
                self.org_group.id,
                self.private_group.id,
                self.member_group.id,
            },
        )


class ProjectMemberTestCase(PeopleGroupPublicationStatusTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_authenticate(self.member)

    def test_retrieve_people_groups(self):
        for people_group in [
            self.public_group,
            self.private_group,
            self.org_group,
            self.member_group,
        ]:
            response = self.client.get(
                reverse(
                    "PeopleGroup-detail",
                    args=(
                        self.organization.code,
                        people_group.id,
                    ),
                )
            )
            member_response = self.client.get(
                reverse(
                    "PeopleGroup-member",
                    args=(
                        self.organization.code,
                        people_group.id,
                    ),
                )
            )
            project_response = self.client.get(
                reverse(
                    "PeopleGroup-project",
                    args=(
                        self.organization.code,
                        people_group.id,
                    ),
                )
            )
            if people_group in [self.public_group, self.member_group]:
                self.assertEqual(response.status_code, 200)
                self.assertEqual(member_response.status_code, 200)
                self.assertEqual(project_response.status_code, 200)
            else:
                self.assertEqual(response.status_code, 404)
                self.assertEqual(member_response.status_code, 404)
                self.assertEqual(project_response.status_code, 404)

    def test_list_people_groups(self):
        response = self.client.get(
            reverse("PeopleGroup-list", args=(self.organization.code,))
        )
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 2)
        self.assertEqual(
            {people_group["id"] for people_group in content},
            {self.public_group.id, self.member_group.id},
        )
