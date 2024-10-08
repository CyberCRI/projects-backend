import uuid
from unittest.mock import patch

from django.conf import settings
from django.urls import reverse
from faker import Faker
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.accounts.models import PeopleGroup, ProjectUser
from apps.accounts.utils import get_superadmins_group
from apps.organizations.factories import OrganizationFactory
from services.google.factories import GoogleAccountFactory, GoogleGroupFactory
from services.google.interface import GoogleService
from services.google.models import GoogleAccount, GoogleSyncErrors
from services.google.tasks import (
    create_google_group_task,
    create_google_user_task,
    suspend_google_user_task,
    update_google_group_task,
    update_google_user_task,
)
from services.google.testcases import GoogleTestCase
from services.keycloak.interface import KeycloakService

faker = Faker()


class GoogleTasksTestCase(GoogleTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        superadmin_group = get_superadmins_group()
        cls.user = UserFactory(groups=[superadmin_group])
        cls.organization = OrganizationFactory(code="TEST_GOOGLE_SYNC")

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=self.user)

    @patch("services.keycloak.interface.KeycloakService.send_email")
    @patch("services.google.tasks.create_google_user_task.delay")
    @patch("services.google.interface.GoogleService.service")
    def test_create_google_account(self, mocked, mocked_delay, mocked_send_email):
        mocked_send_email.return_value = {}
        mocked_delay.side_effect = create_google_user_task

        group = GoogleGroupFactory()
        existing_user = GoogleAccountFactory()
        payload = {
            "email": f"{faker.uuid4()}@{faker.domain_name()}",
            "personal_email": f"{faker.uuid4()}@{faker.domain_name()}",
            "given_name": faker.first_name(),
            "family_name": faker.last_name(),
            "roles_to_add": [
                self.organization.get_users().name,
                group.people_group.get_members().name,
            ],
            "create_in_google": True,
            "google_organizational_unit": "/CRI/Test",
        }
        mocked.side_effect = self.google_side_effect(
            [
                self.get_google_user_success(
                    existing_user
                ),  # same username already exists
                self.get_google_user_error(),  # username is available
                self.create_google_user_success(
                    payload["given_name"],
                    payload["family_name"],
                    payload["google_organizational_unit"],
                    email_count=1,
                ),  # user is created
                self.get_google_user_success(),  # user is fetched
                self.add_user_alias_success(),  # alias is added
                self.list_google_groups_success([]),  # user groups are fetched
                self.add_user_to_group_success(),  # user is added to group
            ]
        )
        with (
            patch.object(
                GoogleService, "create_user", wraps=GoogleService.create_user
            ) as mocked_create_user,
            patch.object(
                GoogleService, "add_user_alias", wraps=GoogleService.add_user_alias
            ) as mocked_add_user_alias,
            patch.object(
                GoogleService, "get_user_groups", wraps=GoogleService.get_user_groups
            ) as mocked_get_user_groups,
            patch.object(
                GoogleService,
                "add_user_to_group",
                wraps=GoogleService.add_user_to_group,
            ) as mocked_add_user_to_group,
        ):
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(
                    reverse("ProjectUser-list")
                    + f"?organization={self.organization.code}",
                    data=payload,
                )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            content = response.json()
            user = ProjectUser.objects.get(id=content["id"])
            self.assertIsNotNone(user.google_account)
            mocked_create_user.assert_called_once_with(user, "/CRI/Test")
            mocked_add_user_alias.assert_called_once_with(user.google_account)
            mocked_get_user_groups.assert_called_once_with(user.google_account)
            mocked_add_user_to_group.assert_called_once_with(user.google_account, group)
            keycloak_user = KeycloakService.get_user(user.keycloak_id)
            self.assertEqual(user.email.lower(), user.google_account.email.lower())
            self.assertEqual(user.email.lower(), user.keycloak_account.username.lower())
            self.assertEqual(user.email.lower(), content["email"].lower())
            self.assertEqual(user.email.lower(), keycloak_user["username"].lower())
            self.assertEqual(
                user.email.lower(),
                f"{payload['given_name']}.{payload['family_name']}.1@{settings.GOOGLE_EMAIL_DOMAIN}".lower(),
            )
            self.assertEqual(
                user.personal_email.lower(), user.keycloak_account.email.lower()
            )
            self.assertEqual(
                user.personal_email.lower(), content["personal_email"].lower()
            )
            self.assertEqual(
                user.personal_email.lower(), keycloak_user["email"].lower()
            )
            self.assertEqual(user.personal_email.lower(), payload["email"].lower())
            self.assertEqual(
                user.google_account.organizational_unit,
                payload["google_organizational_unit"],
            )
            self.assertTrue(bool(user.google_account.google_id))
            self.assertFalse(
                GoogleSyncErrors.objects.filter(google_account__user=user).exists()
            )

    @patch("services.google.tasks.update_google_user_task.delay")
    @patch("services.google.interface.GoogleService.service")
    def test_update_google_account(self, mocked, mocked_delay):
        mocked_delay.side_effect = update_google_user_task

        group_1 = GoogleGroupFactory(organization=self.organization)
        group_2 = GoogleGroupFactory(organization=self.organization)
        google_account = GoogleAccountFactory(
            groups=[self.organization.get_users(), group_2.people_group.get_members()],
        )
        payload = {
            "given_name": faker.first_name(),
            "family_name": faker.last_name(),
            "google_organizational_unit": "/CRI/Test update",
        }
        mocked.side_effect = self.google_side_effect(
            [
                self.update_google_user_success(),  # user is updated
                self.list_google_groups_success([group_1]),  # user groups are fetched
                self.remove_user_from_group_success(),  # user is removed from group_1
                self.add_user_to_group_success(
                    google_account
                ),  # user is added to group_2
            ]
        )
        with (
            patch.object(
                GoogleService, "update_user", wraps=GoogleService.update_user
            ) as mocked_update_user,
            patch.object(
                GoogleService, "get_user_groups", wraps=GoogleService.get_user_groups
            ) as mocked_get_user_groups,
            patch.object(
                GoogleService,
                "remove_user_from_group",
                wraps=GoogleService.remove_user_from_group,
            ) as mocked_remove_user_from_group,
            patch.object(
                GoogleService,
                "add_user_to_group",
                wraps=GoogleService.add_user_to_group,
            ) as mocked_add_user_to_group,
        ):
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.patch(
                    reverse("ProjectUser-detail", args=(google_account.user.id,)),
                    data=payload,
                )
            mocked_update_user.assert_called_once_with(google_account)
            mocked_get_user_groups.assert_called_once_with(google_account)
            mocked_remove_user_from_group.assert_called_once_with(
                google_account, group_1
            )
            mocked_add_user_to_group.assert_called_once_with(google_account, group_2)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            google_account.refresh_from_db()
            self.assertEqual(
                google_account.organizational_unit,
                payload["google_organizational_unit"],
            )

    @patch("services.google.tasks.suspend_google_user_task.delay")
    @patch("services.google.interface.GoogleService.service")
    def test_suspend_google_account(self, mocked, mocked_delay):
        mocked_delay.side_effect = suspend_google_user_task
        google_account = GoogleAccountFactory(groups=[self.organization.get_users()])
        google_id = google_account.google_id
        mocked.side_effect = self.google_side_effect(
            [
                self.update_google_user_success(
                    google_account, suspended=True
                ),  # user is suspended
            ]
        )
        with patch.object(
            GoogleService, "suspend_user", wraps=GoogleService.suspend_user
        ) as mocked_suspend_user:
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.delete(
                    reverse("ProjectUser-detail", args=(google_account.user.id,))
                )
            mocked_suspend_user.assert_called_once_with(google_account)
            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
            self.assertFalse(GoogleAccount.objects.filter(google_id=google_id).exists())

    @patch("services.google.tasks.create_google_group_task.delay")
    @patch("services.google.interface.GoogleService.service")
    def test_create_google_group_with_email(self, mocked, mocked_delay):
        mocked_delay.side_effect = create_google_group_task
        google_user = GoogleAccountFactory(groups=[self.organization.get_users()])
        payload = {
            "name": f"googlesync-{uuid.uuid4()}",
            "organization": self.organization.code,
            "create_in_google": True,
            "email": f"googlesync-{uuid.uuid4()}@{settings.GOOGLE_EMAIL_DOMAIN}",
            "description": "",
            "team": {
                "members": [google_user.user.id],
            },
        }
        mocked.side_effect = self.google_side_effect(
            [
                self.get_google_group_error(),  # group email is available
                self.create_google_group_success(
                    email=payload["email"],
                    name=payload["name"],
                ),  # group is created
                self.add_group_alias_success(),  # alias is added
                self.list_group_members_success([]),  # group members are fetched
                self.add_user_to_group_success(),  # user is added to group
            ]
        )
        with (
            patch.object(
                GoogleService, "create_group", wraps=GoogleService.create_group
            ) as mocked_create_group,
            patch.object(
                GoogleService, "add_group_alias", wraps=GoogleService.add_group_alias
            ) as mocked_add_group_alias,
            patch.object(
                GoogleService,
                "get_group_members",
                wraps=GoogleService.get_group_members,
            ) as mocked_get_group_members,
            patch.object(
                GoogleService,
                "add_user_to_group",
                wraps=GoogleService.add_user_to_group,
            ) as mocked_add_user_to_group,
        ):
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(
                    reverse("PeopleGroup-list", args=(self.organization.code,)),
                    data=payload,
                )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            content = response.json()
            people_group = PeopleGroup.objects.get(id=content["id"])
            self.assertIsNotNone(people_group.google_group)
            mocked_create_group.assert_called_once_with(people_group)
            mocked_add_group_alias.assert_called_once_with(people_group.google_group)
            mocked_get_group_members.assert_called_once_with(people_group.google_group)
            mocked_add_user_to_group.assert_called_once_with(
                google_user, people_group.google_group
            )
            self.assertEqual(
                people_group.email.lower(), people_group.google_group.email.lower()
            )
            self.assertEqual(people_group.email.lower(), content["email"].lower())
            self.assertEqual(people_group.email.lower(), payload["email"].lower())
            self.assertTrue(bool(people_group.google_group.google_id))
            self.assertFalse(
                GoogleSyncErrors.objects.filter(
                    google_group__people_group=people_group
                ).exists()
            )

    @patch("services.google.tasks.create_google_group_task.delay")
    @patch("services.google.interface.GoogleService.service")
    def test_create_google_group_with_existing_email(self, mocked, mocked_delay):
        mocked_delay.side_effect = create_google_group_task
        existing_user = GoogleAccountFactory(groups=[self.organization.get_users()])
        existing_group = GoogleGroupFactory(organization=self.organization)
        payload = {
            "name": f"googlesync-{uuid.uuid4()}",
            "organization": self.organization.code,
            "create_in_google": True,
            "email": existing_group.email,
            "description": "",
            "team": {
                "members": [existing_user.user.id],
            },
        }
        mocked.side_effect = self.google_side_effect(
            [
                self.get_google_group_success(
                    existing_group
                ),  # group email is not available
            ]
        )
        with (
            patch.object(
                GoogleService, "create_group", wraps=GoogleService.create_group
            ) as mocked_create_group,
            patch.object(
                GoogleService, "add_group_alias", wraps=GoogleService.add_group_alias
            ) as mocked_add_group_alias,
            patch.object(
                GoogleService,
                "get_group_members",
                wraps=GoogleService.get_group_members,
            ) as mocked_get_group_members,
            patch.object(
                GoogleService,
                "add_user_to_group",
                wraps=GoogleService.add_user_to_group,
            ) as mocked_add_user_to_group,
        ):
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(
                    reverse("PeopleGroup-list", args=(self.organization.code,)),
                    data=payload,
                )
            self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
            content = response.json()
            self.assertEqual(
                content["detail"], "This email is already used by another group"
            )

            mocked_create_group.assert_called_once()
            mocked_add_group_alias.assert_not_called()
            mocked_get_group_members.assert_not_called()
            mocked_add_user_to_group.assert_not_called()
            self.assertFalse(PeopleGroup.objects.filter(name=payload["name"]).exists())

    @patch("services.google.tasks.create_google_group_task.delay")
    @patch("services.google.interface.GoogleService.service")
    def test_create_google_group_without_email(self, mocked, mocked_delay):
        mocked_delay.side_effect = create_google_group_task
        google_user = GoogleAccountFactory(groups=[self.organization.get_users()])
        payload = {
            "name": f"googlesync-{uuid.uuid4()}",
            "organization": self.organization.code,
            "create_in_google": True,
            "description": "",
            "team": {
                "members": [google_user.user.id],
            },
        }
        mocked.side_effect = self.google_side_effect(
            [
                self.get_google_group_success(),  # group email is taken
                self.get_google_group_error(),  # group email is available
                self.create_google_group_success(
                    email=f"{payload['name']}.1@{settings.GOOGLE_EMAIL_DOMAIN}",
                    name=payload["name"],
                ),  # group is created
                self.add_group_alias_success(),  # alias is added
                self.list_group_members_success([]),  # group members are fetched
                self.add_user_to_group_success(),  # user is added to group
            ]
        )
        with (
            patch.object(
                GoogleService, "create_group", wraps=GoogleService.create_group
            ) as mocked_create_group,
            patch.object(
                GoogleService, "add_group_alias", wraps=GoogleService.add_group_alias
            ) as mocked_add_group_alias,
            patch.object(
                GoogleService,
                "get_group_members",
                wraps=GoogleService.get_group_members,
            ) as mocked_get_group_members,
            patch.object(
                GoogleService,
                "add_user_to_group",
                wraps=GoogleService.add_user_to_group,
            ) as mocked_add_user_to_group,
        ):
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(
                    reverse("PeopleGroup-list", args=(self.organization.code,)),
                    data=payload,
                )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            content = response.json()
            people_group = PeopleGroup.objects.get(id=content["id"])
            self.assertIsNotNone(people_group.google_group)
            mocked_create_group.assert_called_once_with(people_group)
            mocked_add_group_alias.assert_called_once_with(people_group.google_group)
            mocked_get_group_members.assert_called_once_with(people_group.google_group)
            mocked_add_user_to_group.assert_called_once_with(
                google_user, people_group.google_group
            )
            self.assertEqual(
                people_group.email.lower(), people_group.google_group.email.lower()
            )
            self.assertEqual(people_group.email.lower(), content["email"].lower())
            self.assertEqual(
                people_group.email.lower(),
                f"{payload['name']}.1@{settings.GOOGLE_EMAIL_DOMAIN}".lower(),
            )
            self.assertTrue(bool(people_group.google_group.google_id))
            self.assertFalse(
                GoogleSyncErrors.objects.filter(
                    google_group__people_group=people_group
                ).exists()
            )

    @patch("services.google.tasks.update_google_group_task.delay")
    @patch("services.google.interface.GoogleService.service")
    def test_update_google_group(self, mocked, mocked_delay):
        mocked_delay.side_effect = update_google_group_task

        google_group = GoogleGroupFactory(organization=self.organization)
        user_1 = GoogleAccountFactory(groups=[self.organization.get_users()])
        user_2 = GoogleAccountFactory(
            groups=[
                self.organization.get_users(),
                google_group.people_group.get_members(),
            ]
        )

        payload = {
            "name": f"{google_group.people_group.name}-updated",
        }
        mocked.side_effect = self.google_side_effect(
            [
                self.update_google_group_success(),  # group is updated
                self.list_group_members_success([user_1]),  # group members are fetched
                self.remove_user_from_group_success(),  # user_2 is removed from group
                self.add_user_to_group_success(user_2),  # user_1 is added to group
            ]
        )
        with (
            patch.object(
                GoogleService, "update_group", wraps=GoogleService.update_group
            ) as mocked_update_group,
            patch.object(
                GoogleService,
                "get_group_members",
                wraps=GoogleService.get_group_members,
            ) as mocked_get_group_members,
            patch.object(
                GoogleService,
                "remove_user_from_group",
                wraps=GoogleService.remove_user_from_group,
            ) as mocked_remove_user_from_group,
            patch.object(
                GoogleService,
                "add_user_to_group",
                wraps=GoogleService.add_user_to_group,
            ) as mocked_add_user_to_group,
        ):
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.patch(
                    reverse(
                        "PeopleGroup-detail",
                        args=(self.organization.code, google_group.people_group.id),
                    ),
                    data=payload,
                )
            mocked_update_group.assert_called_once_with(google_group)
            mocked_get_group_members.assert_called_once_with(google_group)
            mocked_remove_user_from_group.assert_called_once_with(user_1, google_group)
            mocked_add_user_to_group.assert_called_once_with(user_2, google_group)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            google_group.refresh_from_db()
            self.assertEqual(google_group.people_group.name, payload["name"])
