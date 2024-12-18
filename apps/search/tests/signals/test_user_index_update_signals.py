from unittest.mock import patch

from django.urls import reverse
from faker import Faker
from rest_framework import status

from apps.accounts.factories import PeopleGroupFactory, SeedUserFactory, UserFactory
from apps.accounts.models import PeopleGroup, PrivacySettings, ProjectUser
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase
from apps.organizations.factories import OrganizationFactory
from apps.organizations.models import Organization
from apps.projects.factories import ProjectFactory
from apps.projects.models import Project
from apps.skills.factories import SkillFactory, TagFactory

faker = Faker()


class UserIndexUpdateSignalTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.user = SeedUserFactory()
        cls.superadmin = UserFactory(groups=[get_superadmins_group()])

    @patch("services.keycloak.interface.KeycloakService.send_email")
    @patch("apps.search.tasks._update_or_create_user_search_object_task")
    def test_signal_called_on_user_creation(self, signal, email_mock):
        email_mock.return_value = {}
        self.client.force_authenticate(self.superadmin)
        payload = {
            "email": faker.email(),
            "given_name": faker.first_name(),
            "family_name": faker.last_name(),
            "roles_to_add": [self.organization.get_users().name],
        }
        response = self.client.post(
            reverse("ProjectUser-list") + f"?organization={self.organization.code}",
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        content = response.json()
        user = ProjectUser.objects.get(id=content["id"])
        signal.assert_called_with(user.pk)

    @patch("apps.search.tasks.update_or_create_user_search_object_task.delay")
    def test_signal_called_on_user_update(self, signal):
        self.client.force_authenticate(self.superadmin)
        payload = {
            "email": faker.email(),
            "given_name": faker.first_name(),
            "family_name": faker.last_name(),
        }
        response = self.client.patch(
            reverse("ProjectUser-detail", args=(self.user.id,)),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        signal.assert_called_with(self.user.pk)

    @patch("apps.search.tasks.update_or_create_user_search_object_task.delay")
    def test_signal_called_on_user_privacy_update(self, signal):
        self.client.force_authenticate(self.superadmin)
        payload = {"publication_status": PrivacySettings.PrivacyChoices.HIDE}
        response = self.client.patch(
            reverse("PrivacySettings-detail", args=(self.user.id,)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        signal.assert_called_with(self.user.pk)

    @patch("apps.search.tasks.update_or_create_user_search_object_task.delay")
    def test_signal_called_on_add_roles(self, signal):
        self.client.force_authenticate(self.superadmin)
        organization = OrganizationFactory()
        project = ProjectFactory(organizations=[self.organization])
        people_group = PeopleGroupFactory(organization=self.organization)
        payload = {
            "roles_to_add": [
                organization.get_users().name,
                project.get_members().name,
                people_group.get_members().name,
            ]
        }
        response = self.client.patch(
            reverse("ProjectUser-detail", args=(self.user.id,)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        signal.assert_called_with(self.user.pk)

    @patch("apps.search.tasks.update_or_create_user_search_object_task.delay")
    def test_signal_called_on_remove_roles(self, signal):
        self.client.force_authenticate(self.superadmin)
        organization = OrganizationFactory()
        project = ProjectFactory(organizations=[self.organization], with_owner=True)
        people_group = PeopleGroupFactory(organization=self.organization)
        self.user.groups.add(
            project.get_members(), people_group.get_members(), organization.get_users()
        )
        payload = {
            "roles_to_remove": [
                project.get_members().name,
                people_group.get_members().name,
            ]
        }
        response = self.client.patch(
            reverse("ProjectUser-detail", args=(self.user.id,)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        signal.assert_called_with(self.user.pk)

    @patch("apps.search.tasks.update_or_create_user_search_object_task.delay")
    def test_signal_called_on_add_people_group_role(self, signal):
        self.client.force_authenticate(self.superadmin)
        people_group = PeopleGroupFactory(organization=self.organization)
        payload = {
            PeopleGroup.DefaultGroup.MEMBERS: [self.user.id],
        }
        response = self.client.post(
            reverse(
                "PeopleGroup-add-member",
                args=(self.organization.code, people_group.id),
            ),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        signal.assert_called_with(self.user.pk)

    @patch("apps.search.tasks.update_or_create_user_search_object_task.delay")
    def test_signal_called_on_remove_people_group_role(self, signal):
        self.client.force_authenticate(self.superadmin)
        people_group = PeopleGroupFactory(organization=self.organization)
        self.user.groups.add(people_group.get_members())
        payload = {
            "users": [self.user.id],
        }
        response = self.client.post(
            reverse(
                "PeopleGroup-remove-member",
                args=(self.organization.code, people_group.id),
            ),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        signal.assert_called_with(self.user.pk)

    @patch("apps.search.tasks.update_or_create_user_search_object_task.delay")
    def test_signal_called_on_add_project_role(self, signal):
        self.client.force_authenticate(self.superadmin)
        project = ProjectFactory(organizations=[self.organization])
        payload = {
            Project.DefaultGroup.MEMBERS: [self.user.id],
        }
        response = self.client.post(
            reverse("Project-add-member", args=(project.id,)),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        signal.assert_called_with(self.user.pk)

    @patch("apps.search.tasks.update_or_create_user_search_object_task.delay")
    def test_signal_called_on_remove_project_role(self, signal):
        self.client.force_authenticate(self.superadmin)
        project = ProjectFactory(organizations=[self.organization], with_owner=True)
        self.user.groups.add(project.get_members())
        payload = {
            "users": [self.user.id],
        }
        response = self.client.post(
            reverse("Project-remove-member", args=(project.id,)),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        signal.assert_called_with(self.user.pk)

    @patch("apps.search.tasks.update_or_create_user_search_object_task.delay")
    def test_signal_called_on_add_organization_role(self, signal):
        self.client.force_authenticate(self.superadmin)
        organization = OrganizationFactory()
        payload = {
            Organization.DefaultGroup.USERS: [self.user.id],
        }
        response = self.client.post(
            reverse("Organization-add-member", args=(organization.code,)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        signal.assert_called_with(self.user.pk)

    @patch("apps.search.tasks.update_or_create_user_search_object_task.delay")
    def test_signal_called_on_remove_organization_role(self, signal):
        self.client.force_authenticate(self.superadmin)
        organization = OrganizationFactory()
        self.user.groups.add(organization.get_users())
        payload = {
            "users": [self.user.id],
        }
        response = self.client.post(
            reverse("Organization-remove-member", args=(organization.code,)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        signal.assert_called_with(self.user.pk)

    @patch("apps.search.tasks.update_or_create_user_search_object_task.delay")
    def test_signal_called_on_skill_creation(self, signal):
        tag = TagFactory()
        self.client.force_authenticate(self.superadmin)
        payload = {
            "tag": tag.id,
            "level": faker.pyint(1, 4),
            "level_to_reach": faker.pyint(1, 4),
        }
        response = self.client.post(
            reverse("Skill-list", args=(self.user.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        signal.assert_called_with(self.user.pk)

    @patch("apps.search.tasks.update_or_create_user_search_object_task.delay")
    def test_signal_called_on_skill_update(self, signal):
        self.client.force_authenticate(self.superadmin)
        skill = SkillFactory(user=self.user)
        payload = {
            "can_mentor": True,
        }
        response = self.client.patch(
            reverse("Skill-detail", args=(self.user.id, skill.id)),
            data=payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        signal.assert_called_with(self.user.pk)
