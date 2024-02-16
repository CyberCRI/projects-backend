from unittest.mock import patch

from django.urls import reverse
from faker import Faker
from rest_framework import status

from apps.commons.test import JwtAPITestCase
from apps.deploys.models import PostDeployProcess
from apps.deploys.task_managers import InstanceGroupsPermissions
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory

faker = Faker()


class ReassignPermissionTestCase(JwtAPITestCase):
    def _mocked_task_status(self, *args, **kwargs):
        return "STARTED"

    @patch("apps.deploys.models.PostDeployProcess._status")
    def test_reassign_project_permissions(self, mocked):
        mocked.side_effect = self._mocked_task_status
        PostDeployProcess.objects.get_or_create(
            task_name=InstanceGroupsPermissions.task_name
        )
        project = ProjectFactory(with_owner=True)

        for group in project.groups.all():
            group.permissions.clear()
            self.assertEqual(group.permissions.count(), 0)
        project.permissions_up_to_date = False
        project.save()

        self.client.force_authenticate(user=project.get_owners().users.first())
        response = self.client.get(reverse("Project-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        project.refresh_from_db()
        self.assertTrue(project.permissions_up_to_date)

    @patch("apps.deploys.models.PostDeployProcess._status")
    def test_reassign_organization_permissions(self, mocked):
        mocked.side_effect = self._mocked_task_status
        PostDeployProcess.objects.get_or_create(
            task_name=InstanceGroupsPermissions.task_name
        )
        organization = OrganizationFactory(with_admin=True)

        for group in organization.groups.all():
            group.permissions.clear()
            self.assertEqual(group.permissions.count(), 0)
        organization.permissions_up_to_date = False
        organization.save()

        self.client.force_authenticate(user=organization.get_admins().users.first())
        response = self.client.get(reverse("Organization-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        organization.refresh_from_db()
        self.assertTrue(organization.permissions_up_to_date)
