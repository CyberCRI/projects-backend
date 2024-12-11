from django.test import TestCase

from apps.accounts.factories import PeopleGroupFactory
from apps.accounts.utils import get_instance_from_group
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory


class GetInstanceFromGroupTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.organization = OrganizationFactory()
        cls.people_group = PeopleGroupFactory(organization=cls.organization)
        cls.project = ProjectFactory(organizations=[cls.organization])

    def test_get_instance_from_organization_group(self):
        for group in [
            self.organization.get_admins(),
            self.organization.get_facilitators(),
            self.organization.get_users(),
        ]:
            instance = get_instance_from_group(group)
            self.assertEqual(instance, self.organization)

    def test_get_instance_from_people_group_group(self):
        for group in [
            self.people_group.get_leaders(),
            self.people_group.get_managers(),
            self.people_group.get_members(),
        ]:
            instance = get_instance_from_group(group)
            self.assertEqual(instance, self.people_group)

    def test_get_instance_from_project_group(self):
        for group in [
            self.project.get_owners(),
            self.project.get_reviewers(),
            self.project.get_members(),
            self.project.get_people_groups(),
        ]:
            instance = get_instance_from_group(group)
            self.assertEqual(instance, self.project)

    def test_get_instance_from_deleted_group(self):
        project = ProjectFactory(organizations=[self.organization])
        people_group = PeopleGroupFactory(organization=self.organization)
        project.member_people_groups.add(people_group)
        project.delete()
        for group in [
            project.get_owners(),
            project.get_reviewers(),
            project.get_members(),
            project.get_people_groups(),
        ]:
            instance = get_instance_from_group(group)
            self.assertIsNone(instance)
