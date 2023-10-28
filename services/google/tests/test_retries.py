from unittest.mock import patch

from parameterized import parameterized

from services.google.factories import (
    GoogleAccountFactory,
    GoogleGroupFactory,
    GoogleSyncErrorFactory,
)
from services.google.models import GoogleSyncErrors
from services.google.tasks import retry_failed_tasks
from services.google.testcases import GoogleTestCase


class GoogleRetryErrorsTestCase(GoogleTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.google_group = GoogleGroupFactory()
        cls.google_account = GoogleAccountFactory(
            groups=[cls.google_group.people_group.get_members()]
        )

    @parameterized.expand(
        [
            (
                GoogleSyncErrors.OnTaskChoices.CREATE_USER,
                "services.google.models.GoogleAccount.create",
            ),
            (
                GoogleSyncErrors.OnTaskChoices.UPDATE_USER,
                "services.google.models.GoogleAccount.update",
            ),
            (
                GoogleSyncErrors.OnTaskChoices.SUSPEND_USER,
                "services.google.models.GoogleAccount.suspend",
            ),
            (
                GoogleSyncErrors.OnTaskChoices.USER_ALIAS,
                "services.google.models.GoogleAccount.create_alias",
            ),
            (
                GoogleSyncErrors.OnTaskChoices.KEYCLOAK_USERNAME,
                "services.google.models.GoogleAccount.update_keycloak_username",
            ),
            (
                GoogleSyncErrors.OnTaskChoices.SYNC_GROUPS,
                "services.google.models.GoogleAccount.sync_groups",
            ),
        ]
    )
    def test_retry_failed_account_tasks(self, failed_task, mocked_task):
        GoogleSyncErrorFactory(
            google_account=self.google_account, on_task=failed_task, solved=False
        )
        with patch(mocked_task) as mock:
            mock.return_value = None
            retry_failed_tasks()
            mock.assert_called_once()

    @parameterized.expand(
        [
            (
                GoogleSyncErrors.OnTaskChoices.CREATE_GROUP,
                "services.google.models.GoogleGroup.create",
            ),
            (
                GoogleSyncErrors.OnTaskChoices.UPDATE_GROUP,
                "services.google.models.GoogleGroup.update",
            ),
            (
                GoogleSyncErrors.OnTaskChoices.GROUP_ALIAS,
                "services.google.models.GoogleGroup.create_alias",
            ),
            (
                GoogleSyncErrors.OnTaskChoices.SYNC_MEMBERS,
                "services.google.models.GoogleGroup.sync_members",
            ),
        ]
    )
    def test_retry_failed_group_tasks(self, failed_task, mocked_task):
        GoogleSyncErrorFactory(
            google_group=self.google_group, on_task=failed_task, solved=False
        )
        with patch(mocked_task) as mock:
            mock.return_value = None
            retry_failed_tasks()
            mock.assert_called_once()

    @parameterized.expand(
        [
            (
                GoogleSyncErrors.OnTaskChoices.SYNC_MEMBERS,
                "services.google.models.GoogleGroup.sync_members",
            ),
            (
                GoogleSyncErrors.OnTaskChoices.SYNC_GROUPS,
                "services.google.models.GoogleAccount.sync_groups",
            ),
        ]
    )
    def test_retry_failed_account_and_group_tasks(self, failed_task, mocked_task):
        GoogleSyncErrorFactory(
            google_group=self.google_group,
            google_account=self.google_account,
            on_task=failed_task,
            solved=False,
        )
        with patch(mocked_task) as mock:
            mock.return_value = None
            retry_failed_tasks()
            mock.assert_called_once()


class GoogleRetryErrorsIncrementTestCase(GoogleTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.google_group = GoogleGroupFactory()
        cls.google_account = GoogleAccountFactory(
            groups=[cls.google_group.people_group.get_members()]
        )

    @staticmethod
    def side_effect(*args, **kwargs):
        raise Exception("Updated error")

    @staticmethod
    def return_list_side_effect(items):
        def inner(*args, **kwargs):
            return items

        return inner

    @parameterized.expand(
        [
            (
                GoogleSyncErrors.OnTaskChoices.CREATE_USER,
                "services.google.interface.GoogleService.create_user",
            ),
            (
                GoogleSyncErrors.OnTaskChoices.UPDATE_USER,
                "services.google.interface.GoogleService.update_user",
            ),
            (
                GoogleSyncErrors.OnTaskChoices.SUSPEND_USER,
                "services.google.interface.GoogleService.suspend_user",
            ),
            (
                GoogleSyncErrors.OnTaskChoices.USER_ALIAS,
                "services.google.interface.GoogleService.add_user_alias",
            ),
            (
                GoogleSyncErrors.OnTaskChoices.KEYCLOAK_USERNAME,
                "services.keycloak.interface.KeycloakService.update_user",
            ),
            (
                GoogleSyncErrors.OnTaskChoices.SYNC_GROUPS,
                "services.google.interface.GoogleService.get_user_groups",
            ),
        ]
    )
    def test_retry_failure_increment_account_tasks(self, failed_task, mocked_task):
        error = GoogleSyncErrorFactory(
            google_account=self.google_account,
            on_task=failed_task,
            solved=False,
            retries_count=0,
            error="Initial error",
        )
        with patch(mocked_task) as mock:
            mock.side_effect = self.side_effect
            retry_failed_tasks()
            mock.assert_called_once()
            error.refresh_from_db()
            assert error.solved is False
            assert error.retries_count == 1
            assert error.error == "Updated error"

    @parameterized.expand(
        [
            (
                GoogleSyncErrors.OnTaskChoices.CREATE_GROUP,
                "services.google.interface.GoogleService.create_group",
            ),
            (
                GoogleSyncErrors.OnTaskChoices.UPDATE_GROUP,
                "services.google.interface.GoogleService.update_group",
            ),
            (
                GoogleSyncErrors.OnTaskChoices.GROUP_ALIAS,
                "services.google.interface.GoogleService.add_group_alias",
            ),
            (
                GoogleSyncErrors.OnTaskChoices.SYNC_MEMBERS,
                "services.google.interface.GoogleService.get_group_members",
            ),
        ]
    )
    def test_retry_failure_increment_group_tasks(self, failed_task, mocked_task):
        error = GoogleSyncErrorFactory(
            google_group=self.google_group,
            on_task=failed_task,
            solved=False,
            retries_count=0,
            error="Initial error",
        )
        with patch(mocked_task) as mock:
            mock.side_effect = self.side_effect
            retry_failed_tasks()
            mock.assert_called_once()
            error.refresh_from_db()
            assert error.solved is False
            assert error.retries_count == 1
            assert error.error == "Updated error"

    @parameterized.expand(
        [
            (
                GoogleSyncErrors.OnTaskChoices.SYNC_GROUPS,
                "services.google.interface.GoogleService.get_user_groups",
            ),
            (
                GoogleSyncErrors.OnTaskChoices.SYNC_MEMBERS,
                "services.google.interface.GoogleService.get_group_members",
            ),
        ]
    )
    def test_retry_failure_increment_account_and_group_tasks(
        self, failed_task, mocked_task
    ):
        error = GoogleSyncErrorFactory(
            google_group=self.google_group,
            google_account=self.google_account,
            on_task=failed_task,
            solved=False,
            retries_count=0,
            error="Initial error",
        )
        with (
            patch(mocked_task) as mocked_get,
            patch(
                "services.google.interface.GoogleService.add_user_to_group"
            ) as mocked_add,
        ):
            mocked_get.side_effect = self.return_list_side_effect([])
            mocked_add.side_effect = self.side_effect
            retry_failed_tasks()
            mocked_get.assert_called_once()
            mocked_add.assert_called_once()
            error.refresh_from_db()
            assert error.solved is False
            assert error.retries_count == 1
            assert error.error == "Updated error"


class GoogleRetryErrorsSolvedTestCase(GoogleTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.google_group = GoogleGroupFactory()
        cls.google_account = GoogleAccountFactory(
            groups=[cls.google_group.people_group.get_members()]
        )

    @staticmethod
    def return_item_side_effect(item):
        def inner(*args, **kwargs):
            return item

        return inner

    @staticmethod
    def return_list_side_effect(items):
        def inner(*args, **kwargs):
            return items

        return inner

    @parameterized.expand(
        [
            (
                GoogleSyncErrors.OnTaskChoices.CREATE_USER,
                "services.google.interface.GoogleService.create_user",
            ),
            (
                GoogleSyncErrors.OnTaskChoices.UPDATE_USER,
                "services.google.interface.GoogleService.update_user",
            ),
            (
                GoogleSyncErrors.OnTaskChoices.SUSPEND_USER,
                "services.google.interface.GoogleService.suspend_user",
            ),
            (
                GoogleSyncErrors.OnTaskChoices.USER_ALIAS,
                "services.google.interface.GoogleService.add_user_alias",
            ),
            (
                GoogleSyncErrors.OnTaskChoices.KEYCLOAK_USERNAME,
                "services.keycloak.interface.KeycloakService.update_user",
            ),
        ]
    )
    def test_retry_error_solved_account_tasks(self, failed_task, mocked_task):
        error = GoogleSyncErrorFactory(
            google_account=self.google_account,
            on_task=failed_task,
            solved=False,
            retries_count=0,
            error="Initial error",
        )
        returned_value = {
            "primaryEmail": self.google_account.email,
            "id": self.google_account.google_id,
        }
        with patch(mocked_task) as mock:
            mock.side_effect = self.return_item_side_effect(returned_value)
            retry_failed_tasks()
            mock.assert_called_once()
            error.refresh_from_db()
            assert error.solved is True
            assert error.retries_count == 1
            assert error.error == "Initial error"

    @parameterized.expand(
        [
            (
                GoogleSyncErrors.OnTaskChoices.CREATE_GROUP,
                "services.google.interface.GoogleService.create_group",
            ),
            (
                GoogleSyncErrors.OnTaskChoices.UPDATE_GROUP,
                "services.google.interface.GoogleService.update_group",
            ),
            (
                GoogleSyncErrors.OnTaskChoices.GROUP_ALIAS,
                "services.google.interface.GoogleService.add_group_alias",
            ),
        ]
    )
    def test_retry_error_solved_group_tasks(self, failed_task, mocked_task):
        error = GoogleSyncErrorFactory(
            google_group=self.google_group,
            on_task=failed_task,
            solved=False,
            retries_count=0,
            error="Initial error",
        )
        returned_value = {
            "email": self.google_group.email,
            "id": self.google_group.google_id,
        }
        with patch(mocked_task) as mock:
            mock.side_effect = self.return_item_side_effect(returned_value)
            retry_failed_tasks()
            mock.assert_called_once()
            error.refresh_from_db()
            assert error.solved is True
            assert error.retries_count == 1
            assert error.error == "Initial error"

    @parameterized.expand(
        [
            (
                GoogleSyncErrors.OnTaskChoices.SYNC_GROUPS,
                "services.google.interface.GoogleService.get_user_groups",
                False,
                True,
            ),
            (
                GoogleSyncErrors.OnTaskChoices.SYNC_GROUPS,
                "services.google.interface.GoogleService.get_user_groups",
                True,
                True,
            ),
            (
                GoogleSyncErrors.OnTaskChoices.SYNC_MEMBERS,
                "services.google.interface.GoogleService.get_group_members",
                True,
                False,
            ),
            (
                GoogleSyncErrors.OnTaskChoices.SYNC_MEMBERS,
                "services.google.interface.GoogleService.get_group_members",
                True,
                True,
            ),
        ]
    )
    def test_retry_error_sync_user_groups_tasks(
        self, failed_task, mocked_task, include_group, include_account
    ):
        error = GoogleSyncErrorFactory(
            google_group=self.google_group if include_group else None,
            google_account=self.google_account if include_account else None,
            on_task=failed_task,
            solved=False,
            retries_count=0,
            error="Initial error",
        )
        with (
            patch(mocked_task) as mocked_get,
            patch(
                "services.google.interface.GoogleService.add_user_to_group"
            ) as mocked_add,
        ):
            mocked_get.side_effect = self.return_item_side_effect([])
            mocked_add.side_effect = self.return_item_side_effect({})
            retry_failed_tasks()
            mocked_get.assert_called_once()
            error.refresh_from_db()
            assert error.solved is True
            assert error.retries_count == 1
            assert error.error == "Initial error"
