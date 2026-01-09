from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

from apps.accounts.factories import PeopleGroupFactory, UserFactory
from apps.accounts.models import PeopleGroup
from apps.commons.models import GroupData
from apps.commons.test import JwtAPITestCase
from apps.deploys.tasks import (
    reassign_organizations_permissions,
    reassign_people_groups_permissions,
    reassign_projects_permissions,
)
from apps.organizations.factories import OrganizationFactory
from apps.organizations.models import Organization
from apps.projects.factories import ProjectFactory
from apps.projects.models import Project


class PermissionsSetupTestCase(JwtAPITestCase):
    """Test permissions setup post-deploy tasks"""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()

    def test_organization_permissions_setup(self):
        """Test organization permissions setup"""
        # Setup test data
        organization = self.organization
        admin = UserFactory(groups=[organization.get_admins()])
        facilitator = UserFactory(groups=[organization.get_facilitators()])
        user = UserFactory(groups=[organization.get_users()])

        # Get roles permissions
        all_permissions = Permission.objects.filter(
            content_type=ContentType.objects.get_for_model(Organization)
        )
        admins_permissions = Organization.get_default_admins_permissions()
        global_admins_permissions = Organization.get_global_admins_permissions()
        facilitators_permissions = Organization.get_default_facilitators_permissions()
        users_permissions = Organization.get_default_users_permissions()

        # Test instance permission setup
        Organization.objects.filter(id=organization.id).update(
            permissions_up_to_date=False
        )
        organization.setup_permissions()
        organization.refresh_from_db()

        self.assertTrue(organization.permissions_up_to_date)
        self.assertEqual(organization.groups.count(), 3)

        for role, permissions in [
            (admin, admins_permissions),
            (facilitator, facilitators_permissions),
            (user, users_permissions),
        ]:
            for perm in all_permissions:
                if perm in permissions:
                    self.assertTrue(role.has_perm(perm.codename, organization))
                else:
                    self.assertFalse(role.has_perm(perm.codename, organization))
        for perm in global_admins_permissions:
            self.assertTrue(admin.has_perm(f"accounts.{perm.codename}"))

        # Test whole class permission reassignment
        reassign_organizations_permissions()
        organization.refresh_from_db()

        self.assertTrue(organization.permissions_up_to_date)
        self.assertEqual(organization.groups.count(), 3)
        for role, permissions in [
            (admin, admins_permissions),
            (facilitator, facilitators_permissions),
            (user, users_permissions),
        ]:
            for perm in all_permissions:
                if perm in permissions:
                    self.assertTrue(role.has_perm(perm.codename, organization))
                else:
                    self.assertFalse(role.has_perm(perm.codename, organization))
        for perm in global_admins_permissions:
            self.assertTrue(admin.has_perm(f"accounts.{perm.codename}"))

        # Test permission reassignment with a permission removed
        removed_permission = users_permissions.first()
        Organization.batch_reassign_permissions(
            roles_permissions=(
                (
                    GroupData.Role.USERS,
                    users_permissions.exclude(id=removed_permission.id),
                ),
            ),
        )
        self.assertFalse(user.has_perm(removed_permission.codename, organization))

    def test_project_permissions_setup(self):
        """Test project permissions setup"""
        # Setup test data
        project = ProjectFactory(organizations=[self.organization])
        owner_people_group = PeopleGroupFactory(organization=self.organization)
        reviewer_people_group = PeopleGroupFactory(organization=self.organization)
        member_people_group = PeopleGroupFactory(organization=self.organization)
        project.owner_groups.add(owner_people_group)
        project.reviewer_groups.add(reviewer_people_group)
        project.member_groups.add(member_people_group)
        owner = UserFactory(groups=[project.get_owners()])
        reviewer = UserFactory(groups=[project.get_reviewers()])
        member = UserFactory(groups=[project.get_members()])
        owner_group_member = UserFactory(
            groups=[project.get_owner_groups(), owner_people_group.get_members()]
        )
        reviewer_group_member = UserFactory(
            groups=[project.get_reviewer_groups(), reviewer_people_group.get_members()]
        )
        member_group_member = UserFactory(
            groups=[project.get_member_groups(), member_people_group.get_members()]
        )

        # Get roles permissions
        all_permissions = Permission.objects.filter(
            content_type=ContentType.objects.get_for_model(Project)
        )
        owners_permissions = Project.get_default_owners_permissions()
        reviewers_permissions = Project.get_default_reviewers_permissions()
        members_permissions = Project.get_default_members_permissions()

        # Test instance permission setup
        Project.objects.filter(id=project.id).update(permissions_up_to_date=False)
        project.setup_permissions()
        project.refresh_from_db()

        self.assertTrue(project.permissions_up_to_date)
        self.assertEqual(project.groups.count(), 6)
        for role, permissions in [
            (owner, owners_permissions),
            (reviewer, reviewers_permissions),
            (member, members_permissions),
            (owner_group_member, owners_permissions),
            (reviewer_group_member, reviewers_permissions),
            (member_group_member, members_permissions),
        ]:
            for perm in all_permissions:
                if perm in permissions:
                    self.assertTrue(role.has_perm(perm.codename, project))
                else:
                    self.assertFalse(role.has_perm(perm.codename, project))

        # Test whole class permission reassignment
        reassign_projects_permissions()
        project.refresh_from_db()

        self.assertTrue(project.permissions_up_to_date)
        self.assertEqual(project.groups.count(), 6)
        for role, permissions in [
            (owner, owners_permissions),
            (reviewer, reviewers_permissions),
            (member, members_permissions),
            (owner_group_member, owners_permissions),
            (reviewer_group_member, reviewers_permissions),
            (member_group_member, members_permissions),
        ]:
            for perm in all_permissions:
                if perm in permissions:
                    self.assertTrue(role.has_perm(perm.codename, project))
                else:
                    self.assertFalse(role.has_perm(perm.codename, project))

        # Test permission reassignment with a permission removed
        removed_permission = members_permissions.first()
        Project.batch_reassign_permissions(
            roles_permissions=(
                (
                    GroupData.Role.MEMBERS,
                    members_permissions.exclude(id=removed_permission.id),
                ),
                (
                    GroupData.Role.MEMBER_GROUPS,
                    members_permissions.exclude(id=removed_permission.id),
                ),
            ),
        )
        self.assertFalse(member.has_perm(removed_permission.codename, project))
        self.assertFalse(
            member_group_member.has_perm(removed_permission.codename, project)
        )

    def test_peoplegroup_permissions_setup(self):
        """Test people group permissions setup"""
        # Setup test data
        people_group = PeopleGroupFactory()
        PeopleGroup.objects.filter(id=people_group.id).update(
            permissions_up_to_date=False
        )
        leader = UserFactory(groups=[people_group.get_leaders()])
        manager = UserFactory(groups=[people_group.get_managers()])
        member = UserFactory(groups=[people_group.get_members()])

        # Get roles permissions
        all_permissions = Permission.objects.filter(
            content_type=ContentType.objects.get_for_model(PeopleGroup)
        )
        leaders_permissions = PeopleGroup.get_default_leaders_permissions()
        managers_permissions = PeopleGroup.get_default_managers_permissions()
        members_permissions = PeopleGroup.get_default_members_permissions()

        # Test instance permission setup
        PeopleGroup.objects.filter(id=people_group.id).update(
            permissions_up_to_date=False
        )
        people_group.setup_permissions()
        people_group.refresh_from_db()

        self.assertTrue(people_group.permissions_up_to_date)
        self.assertEqual(people_group.groups.count(), 3)
        for role, permissions in [
            (leader, leaders_permissions),
            (manager, managers_permissions),
            (member, members_permissions),
        ]:
            for perm in all_permissions:
                if perm in permissions:
                    self.assertTrue(role.has_perm(perm.codename, people_group))
                else:
                    self.assertFalse(role.has_perm(perm.codename, people_group))

        # Test whole class permission reassignment
        reassign_people_groups_permissions()
        people_group.refresh_from_db()

        self.assertTrue(people_group.permissions_up_to_date)
        self.assertEqual(people_group.groups.count(), 3)
        for role, permissions in [
            (leader, leaders_permissions),
            (manager, managers_permissions),
            (member, members_permissions),
        ]:
            for perm in all_permissions:
                if perm in permissions:
                    self.assertTrue(role.has_perm(perm.codename, people_group))
                else:
                    self.assertFalse(role.has_perm(perm.codename, people_group))

        # Test permission reassignment with a permission removed
        removed_permission = members_permissions.first()
        PeopleGroup.batch_reassign_permissions(
            roles_permissions=(
                (
                    GroupData.Role.MEMBERS,
                    members_permissions.exclude(id=removed_permission.id),
                ),
            ),
        )
        self.assertFalse(member.has_perm(removed_permission.codename, people_group))
