from django.urls import reverse
from faker import Faker

from apps.commons.test import JwtAPITestCase
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory

faker = Faker()


class ReassignPermissionTestCase(JwtAPITestCase):
    def test_reassign_project_permissions(self):
        project = ProjectFactory()

        for group in project.groups.all():
            group.permissions.clear()
            assert group.permissions.count() == 0
        project.permissions_up_to_date = False
        project.save()

        self.client.force_authenticate(user=project.get_owners().users.first())
        response = self.client.get(reverse("Project-list"))
        assert response.status_code == 200
        project.refresh_from_db()
        assert project.permissions_up_to_date is True

    def test_reassign_organization_permissions(self):
        organization = OrganizationFactory()

        for group in organization.groups.all():
            group.permissions.clear()
            assert group.permissions.count() == 0
        organization.permissions_up_to_date = False
        organization.save()

        self.client.force_authenticate(user=organization.get_admins().users.first())
        response = self.client.get(reverse("Organization-list"))
        assert response.status_code == 200
        organization.refresh_from_db()
        assert organization.permissions_up_to_date is True
