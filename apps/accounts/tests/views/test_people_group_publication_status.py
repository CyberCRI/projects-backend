from django.urls import reverse
from parameterized import parameterized

from apps.accounts.factories import PeopleGroupFactory
from apps.accounts.models import PeopleGroup, ProjectUser
from apps.commons.test import JwtAPITestCase, TestRoles
from apps.organizations.factories import OrganizationFactory


class PeopleGroupPublicationStatusTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        PeopleGroup.objects.all().delete()  # Delete people_groups created by the factories
        cls.groups = {
            "public": PeopleGroupFactory(
                publication_status=PeopleGroup.PublicationStatus.PUBLIC,
                organization=cls.organization,
            ),
            "private": PeopleGroupFactory(
                publication_status=PeopleGroup.PublicationStatus.PRIVATE,
                organization=cls.organization,
            ),
            "org": PeopleGroupFactory(
                publication_status=PeopleGroup.PublicationStatus.ORG,
                organization=cls.organization,
            ),
            "member": PeopleGroupFactory(
                publication_status=PeopleGroup.PublicationStatus.PRIVATE,
                organization=cls.organization,
            ),
            "root": PeopleGroup.update_or_create_root(cls.organization),
        }
        ProjectUser.objects.all().delete()  # Delete users created by the factories

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, ("public",)),
            (TestRoles.DEFAULT, ("public",)),
            (TestRoles.SUPERADMIN, ("public", "private", "org", "member", "root")),
            (TestRoles.ORG_ADMIN, ("public", "private", "org", "member", "root")),
            (TestRoles.ORG_FACILITATOR, ("public", "private", "org", "member", "root")),
            (TestRoles.ORG_USER, ("public", "org", "root")),
            (TestRoles.GROUP_LEADER, ("public", "member")),
            (TestRoles.GROUP_MANAGER, ("public", "member")),
            (TestRoles.GROUP_MEMBER, ("public", "member")),
        ]
    )
    def test_retrieve_people_groups(self, role, expected_groups):
        organization = self.organization
        member_group = self.groups["member"]
        user = self.get_parameterized_test_user(role, instances=[member_group])
        self.client.force_authenticate(user)
        for people_group_type, people_group in self.groups.items():
            response = self.client.get(
                reverse(
                    "PeopleGroup-detail",
                    args=(
                        organization.code,
                        people_group.id,
                    ),
                )
            )
            member_response = self.client.get(
                reverse(
                    "PeopleGroup-member",
                    args=(
                        organization.code,
                        people_group.id,
                    ),
                )
            )
            project_response = self.client.get(
                reverse(
                    "PeopleGroup-project",
                    args=(
                        organization.code,
                        people_group.id,
                    ),
                )
            )
            if people_group_type in expected_groups:
                self.assertEqual(response.status_code, 200)
                self.assertEqual(member_response.status_code, 200)
                self.assertEqual(project_response.status_code, 200)
            else:
                self.assertEqual(response.status_code, 404)
                self.assertEqual(member_response.status_code, 404)
                self.assertEqual(project_response.status_code, 404)

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, ("public",)),
            (TestRoles.DEFAULT, ("public",)),
            (TestRoles.SUPERADMIN, ("public", "private", "org", "member", "root")),
            (TestRoles.ORG_ADMIN, ("public", "private", "org", "member", "root")),
            (TestRoles.ORG_FACILITATOR, ("public", "private", "org", "member", "root")),
            (TestRoles.ORG_USER, ("public", "org", "root")),
            (TestRoles.GROUP_LEADER, ("public", "member")),
            (TestRoles.GROUP_MANAGER, ("public", "member")),
            (TestRoles.GROUP_MEMBER, ("public", "member")),
        ]
    )
    def test_list_people_groups(self, role, expected_groups):
        organization = self.organization
        member_group = self.groups["member"]
        user = self.get_parameterized_test_user(role, instances=[member_group])
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("PeopleGroup-list", args=(organization.code,))
        )
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), len(expected_groups))
        self.assertEqual(
            {people_group["id"] for people_group in content},
            {
                self.groups[people_group_type].id
                for people_group_type in expected_groups
            },
        )
