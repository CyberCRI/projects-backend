from unittest.mock import call, patch

from django.db.models.query import QuerySet
from django.test import override_settings
from django.urls import reverse
from faker import Faker
from rest_framework import status

from apps.accounts.factories import PeopleGroupFactory, SeedUserFactory, UserFactory
from apps.accounts.models import ProjectUser
from apps.accounts.utils import get_superadmins_group
from apps.commons.models import GroupData
from apps.commons.test import JwtAPITestCase
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory
from apps.skills.factories import SkillFactory, TagFactory

faker = Faker()


class UserIndexUpdateSignalTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.superadmin = UserFactory(groups=[get_superadmins_group()])
        cls.user = SeedUserFactory()

        cls.organization = OrganizationFactory()
        cls.people_group = PeopleGroupFactory(organization=cls.organization)
        cls.project = ProjectFactory(organizations=[cls.organization])
        cls.project_main_owner = UserFactory(groups=[cls.project.get_owners()])

        cls.tag = TagFactory(organization=cls.organization)
        cls.skill_tag = TagFactory(organization=cls.organization)
        cls.skill = SkillFactory(user=cls.user, tag=cls.skill_tag)
        cls.skill_to_delete = SkillFactory(user=cls.user, tag=cls.skill_tag)

        cls.role_remove_member = SeedUserFactory(groups=[cls.organization.get_users()])
        cls.project_remove_member = SeedUserFactory(groups=[cls.project.get_members()])
        cls.people_group_remove_member = SeedUserFactory(
            groups=[cls.people_group.get_members()]
        )
        cls.organization_remove_member = SeedUserFactory(
            groups=[cls.organization.get_users()]
        )

    @staticmethod
    def mocked_update(*args, **kwargs):
        pass

    @override_settings(OPENSEARCH_DSL_AUTO_REFRESH=True, OPENSEARCH_DSL_AUTOSYNC=True)
    @patch("django_opensearch_dsl.documents.Document.update")
    @patch("services.keycloak.interface.KeycloakService.send_email")
    def test_signal_called_on_user_creation(self, mocked_email, mocked_update):
        mocked_email.return_value = {}
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
        mocked_update.assert_has_calls(
            [call(ProjectUser.objects.get(id=response.json()["id"]), "index")]
        )

    @override_settings(OPENSEARCH_DSL_AUTO_REFRESH=True, OPENSEARCH_DSL_AUTOSYNC=True)
    @patch("django_opensearch_dsl.documents.Document.update")
    def test_signal_called_on_user_update(self, mocked_update):
        mocked_update.side_effect = self.mocked_update

        self.client.force_authenticate(self.superadmin)
        payload = {"given_name": faker.first_name()}
        response = self.client.patch(
            reverse("ProjectUser-detail", args=(self.user.id,)), payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mocked_update.assert_has_calls([call(self.user, "index")])

    @override_settings(OPENSEARCH_DSL_AUTO_REFRESH=True, OPENSEARCH_DSL_AUTOSYNC=True)
    @patch("django_opensearch_dsl.documents.Document.update")
    def test_signal_called_on_add_role(self, mocked_update):
        mocked_update.side_effect = self.mocked_update

        self.client.force_authenticate(self.superadmin)
        payload = {"roles_to_add": [self.organization.get_users().name]}
        response = self.client.patch(
            reverse("ProjectUser-detail", args=(self.user.id,)), payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mocked_update.assert_has_calls([call(self.user, "index")])

    @override_settings(OPENSEARCH_DSL_AUTO_REFRESH=True, OPENSEARCH_DSL_AUTOSYNC=True)
    @patch("django_opensearch_dsl.documents.Document.update")
    def test_signal_called_on_remove_role(self, mocked_update):
        mocked_update.side_effect = self.mocked_update

        self.client.force_authenticate(self.superadmin)
        payload = {"roles_to_remove": [self.organization.get_users().name]}
        response = self.client.patch(
            reverse("ProjectUser-detail", args=(self.role_remove_member.id,)), payload
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        mocked_update.assert_has_calls([call(self.role_remove_member, "index")])

    @override_settings(OPENSEARCH_DSL_AUTO_REFRESH=True, OPENSEARCH_DSL_AUTOSYNC=True)
    @patch("django_opensearch_dsl.documents.Document.update")
    def test_signal_called_on_add_people_group_member(self, mocked_update):
        mocked_update.side_effect = self.mocked_update

        self.client.force_authenticate(self.superadmin)
        payload = {GroupData.Role.MEMBERS: [self.user.id]}
        response = self.client.post(
            reverse(
                "PeopleGroup-add-member",
                args=(self.organization.code, self.people_group.id),
            ),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        mocked_update.assert_has_calls([call(self.user, "index")])

    @override_settings(OPENSEARCH_DSL_AUTO_REFRESH=True, OPENSEARCH_DSL_AUTOSYNC=True)
    @patch("django_opensearch_dsl.documents.Document.update")
    def test_signal_called_on_remove_people_group_member(self, mocked_update):
        mocked_update.side_effect = self.mocked_update

        self.client.force_authenticate(self.superadmin)
        payload = {"users": [self.people_group_remove_member.id]}
        response = self.client.post(
            reverse(
                "PeopleGroup-remove-member",
                args=(self.organization.code, self.people_group.id),
            ),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        mocked_update.assert_has_calls([call(self.people_group_remove_member, "index")])

    @override_settings(OPENSEARCH_DSL_AUTO_REFRESH=True, OPENSEARCH_DSL_AUTOSYNC=True)
    @patch("django_opensearch_dsl.documents.Document.update")
    def test_signal_called_on_add_project_member(self, mocked_update):
        mocked_update.side_effect = self.mocked_update

        self.client.force_authenticate(self.superadmin)
        payload = {GroupData.Role.MEMBERS: [self.user.id]}
        response = self.client.post(
            reverse("Project-add-member", args=(self.project.id,)),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        mocked_update.assert_has_calls([call(self.user, "index")])

    @override_settings(OPENSEARCH_DSL_AUTO_REFRESH=True, OPENSEARCH_DSL_AUTOSYNC=True)
    @patch("django_opensearch_dsl.documents.Document.update")
    def test_signal_called_on_remove_project_member(self, mocked_update):
        mocked_update.side_effect = self.mocked_update

        self.client.force_authenticate(self.superadmin)
        payload = {"users": [self.project_remove_member.id]}
        response = self.client.post(
            reverse("Project-remove-member", args=(self.project.id,)),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        mocked_update.assert_has_calls([call(self.project_remove_member, "index")])

    @override_settings(OPENSEARCH_DSL_AUTO_REFRESH=True, OPENSEARCH_DSL_AUTOSYNC=True)
    @patch("django_opensearch_dsl.documents.Document.update")
    def test_signal_called_on_add_organization_member(self, mocked_update):
        mocked_update.side_effect = self.mocked_update

        self.client.force_authenticate(self.superadmin)
        payload = {"users": [self.user.id]}
        response = self.client.post(
            reverse("Organization-add-member", args=(self.organization.code,)),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        mocked_update.assert_has_calls([call(self.user, "index")])

    @override_settings(OPENSEARCH_DSL_AUTO_REFRESH=True, OPENSEARCH_DSL_AUTOSYNC=True)
    @patch("django_opensearch_dsl.documents.Document.update")
    def test_signal_called_on_remove_organization_member(self, mocked_update):
        mocked_update.side_effect = self.mocked_update

        self.client.force_authenticate(self.superadmin)
        payload = {"users": [self.organization_remove_member.id]}
        response = self.client.post(
            reverse("Organization-remove-member", args=(self.organization.code,)),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        mocked_update.assert_has_calls([call(self.organization_remove_member, "index")])

    @override_settings(OPENSEARCH_DSL_AUTO_REFRESH=True, OPENSEARCH_DSL_AUTOSYNC=True)
    @patch("django_opensearch_dsl.documents.Document.update")
    def test_signal_called_on_add_skill(self, mocked_update):
        mocked_update.side_effect = self.mocked_update

        self.client.force_authenticate(self.superadmin)
        payload = {
            "tag": self.tag.id,
            "level": faker.pyint(1, 4),
            "level_to_reach": faker.pyint(1, 4),
        }
        response = self.client.post(
            reverse("Skill-list", args=(self.user.id,)), data=payload
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        mocked_update.assert_has_calls([call(self.user, "index")])

    @override_settings(OPENSEARCH_DSL_AUTO_REFRESH=True, OPENSEARCH_DSL_AUTOSYNC=True)
    @patch("django_opensearch_dsl.documents.Document.update")
    def test_signal_called_on_change_skill(self, mocked_update):
        mocked_update.side_effect = self.mocked_update

        self.client.force_authenticate(self.superadmin)
        title = faker.word()
        payload = {"title": title, "title_en": title, "title_fr": title}
        response = self.client.patch(
            reverse(
                "OrganizationTag-detail",
                args=(self.organization.code, self.skill_tag.id),
            ),
            payload,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            any(
                self.user in call_args[0][0] and call_args[0][1] == "index"
                for call_args in mocked_update.call_args_list
                if len(call_args[0]) == 2
                and isinstance(call_args[0][0], QuerySet)
                and call_args[0][0].model == ProjectUser
            )
        )

    @override_settings(OPENSEARCH_DSL_AUTO_REFRESH=True, OPENSEARCH_DSL_AUTOSYNC=True)
    @patch("django_opensearch_dsl.documents.Document.update")
    def test_signal_called_on_delete_skill(self, mocked_update):
        mocked_update.side_effect = self.mocked_update

        self.client.force_authenticate(self.superadmin)
        response = self.client.delete(
            reverse("Skill-detail", args=(self.user.id, self.skill_to_delete.id))
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        mocked_update.assert_has_calls([call(self.user, "index", raise_on_error=False)])
