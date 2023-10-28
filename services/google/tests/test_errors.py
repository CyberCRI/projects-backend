from unittest.mock import patch

from apps.accounts.factories import PeopleGroupFactory, SeedUserFactory, UserFactory
from apps.accounts.utils import get_superadmins_group
from apps.organizations.factories import OrganizationFactory
from services.google.factories import (
    GoogleAccountFactory,
    GoogleGroupFactory,
    GoogleSyncErrorFactory,
)
from services.google.models import GoogleAccount, GoogleGroup, GoogleSyncErrors
from services.google.tasks import (
    create_google_account,
    create_google_group,
    create_google_group_task,
    create_google_user_task,
    suspend_google_account,
    suspend_google_user_task,
    update_google_account,
    update_google_group,
    update_google_group_task,
    update_google_user_task,
)
from services.google.testcases import GoogleTestCase


class GoogleCreateUserErrorTestCase(GoogleTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        superadmin_group = get_superadmins_group()
        cls.user = UserFactory(groups=[superadmin_group])
        cls.organization = OrganizationFactory(code="TEST_GOOGLE_SYNC")

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=self.user)

    @patch("services.google.tasks.create_google_user_task.delay")
    @patch("services.google.interface.GoogleService.service")
    def test_create_google_account_create_error(self, mocked, mocked_delay):
        mocked_delay.side_effect = create_google_user_task
        group = GoogleGroupFactory(organization=self.organization)
        user = SeedUserFactory(
            groups=[self.organization.get_users(), group.people_group.get_members()]
        )
        google_account = GoogleAccount.objects.create(user=user)
        GoogleSyncErrorFactory(
            google_account=google_account,
            on_task=GoogleSyncErrors.OnTaskChoices.CREATE_USER,
            solved=True,
        )
        GoogleSyncErrorFactory(
            google_account=google_account,
            on_task=GoogleSyncErrors.OnTaskChoices.KEYCLOAK_USERNAME,
            solved=True,
        )
        GoogleSyncErrorFactory(
            google_account=google_account,
            on_task=GoogleSyncErrors.OnTaskChoices.USER_ALIAS,
            solved=True,
        )
        GoogleSyncErrorFactory(
            google_account=google_account,
            on_task=GoogleSyncErrors.OnTaskChoices.SYNC_GROUPS,
            solved=True,
        )
        mocked.side_effect = self.google_side_effect(
            [
                self.get_google_user_error(),  # username is available
                self.create_google_user_error(),  # user creation error
            ]
        )
        create_google_account(user, "/CRI/Test")
        previous_errors = GoogleSyncErrors.objects.filter(
            google_account__user=user, solved=True
        )
        errors = GoogleSyncErrors.objects.filter(
            google_account__user=user, solved=False
        )
        assert previous_errors.count() == 4
        assert errors.count() == 4
        assert [e.on_task for e in errors.order_by("created_at")] == [
            GoogleSyncErrors.OnTaskChoices.CREATE_USER,
            GoogleSyncErrors.OnTaskChoices.KEYCLOAK_USERNAME,
            GoogleSyncErrors.OnTaskChoices.USER_ALIAS,
            GoogleSyncErrors.OnTaskChoices.SYNC_GROUPS,
        ]
        assert all(e.google_group is None for e in errors)
        assert all(e.google_account == user.google_account for e in errors)
        assert all(e.retries_count == 0 for e in errors)

    @patch("services.google.tasks.create_google_user_task.delay")
    @patch("services.google.interface.GoogleService.service")
    def test_create_google_account_alias_error(self, mocked, mocked_delay):
        mocked_delay.side_effect = create_google_user_task
        group = GoogleGroupFactory(organization=self.organization)
        user = SeedUserFactory(
            groups=[self.organization.get_users(), group.people_group.get_members()]
        )
        google_account = GoogleAccount.objects.create(user=user)
        GoogleSyncErrorFactory(
            google_account=google_account,
            on_task=GoogleSyncErrors.OnTaskChoices.USER_ALIAS,
            solved=True,
        )
        mocked.side_effect = self.google_side_effect(
            [
                self.get_google_user_error(),  # username is available
                self.create_google_user_success(
                    user.given_name, user.family_name, "/CRI/Test"
                ),  # user created
                self.get_google_user_success(),  # user exists
                self.add_user_alias_error(),  # user alias error
                self.list_google_groups_success([]),  # user groups are fetched
                self.add_user_to_group_success(),  # user is added to group
            ]
        )
        create_google_account(user, "/CRI/Test")
        previous_errors = GoogleSyncErrors.objects.filter(
            google_account__user=user, solved=True
        )
        errors = GoogleSyncErrors.objects.filter(
            google_account__user=user, solved=False
        )
        assert previous_errors.count() == 1
        assert errors.count() == 1
        assert errors[0].on_task == GoogleSyncErrors.OnTaskChoices.USER_ALIAS
        assert errors[0].google_group is None
        assert errors[0].google_account == user.google_account
        assert errors[0].retries_count == 0

    @patch("services.google.tasks.create_google_user_task.delay")
    @patch("services.google.interface.GoogleService.service")
    def test_create_google_account_sync_groups_error(self, mocked, mocked_delay):
        mocked_delay.side_effect = create_google_user_task
        group = GoogleGroupFactory(organization=self.organization)
        user = SeedUserFactory(
            groups=[self.organization.get_users(), group.people_group.get_members()]
        )
        google_account = GoogleAccount.objects.create(user=user)
        GoogleSyncErrorFactory(
            google_account=google_account,
            on_task=GoogleSyncErrors.OnTaskChoices.SYNC_GROUPS,
            solved=True,
        )
        mocked.side_effect = self.google_side_effect(
            [
                self.get_google_user_error(),  # username is available
                self.create_google_user_success(
                    user.given_name, user.family_name, "/CRI/Test"
                ),  # user created
                self.get_google_user_success(),  # user exists
                self.add_user_alias_success(),  # user alias created
                self.list_google_groups_error(),  # user groups error
            ]
        )
        create_google_account(user, "/CRI/Test")
        previous_errors = GoogleSyncErrors.objects.filter(
            google_account__user=user, solved=True
        )
        errors = GoogleSyncErrors.objects.filter(
            google_account__user=user, solved=False
        )
        assert previous_errors.count() == 1
        assert errors.count() == 1
        assert errors[0].on_task == GoogleSyncErrors.OnTaskChoices.SYNC_GROUPS
        assert errors[0].google_group is None
        assert errors[0].google_account == user.google_account
        assert errors[0].retries_count == 0

    @patch("services.google.tasks.create_google_user_task.delay")
    @patch("services.google.interface.GoogleService.service")
    def test_create_google_account_sync_group_error(self, mocked, mocked_delay):
        mocked_delay.side_effect = create_google_user_task
        group = GoogleGroupFactory(organization=self.organization)
        user = SeedUserFactory(
            groups=[self.organization.get_users(), group.people_group.get_members()]
        )
        google_account = GoogleAccount.objects.create(user=user)
        GoogleSyncErrorFactory(
            google_account=google_account,
            on_task=GoogleSyncErrors.OnTaskChoices.SYNC_GROUPS,
            solved=True,
        )
        mocked.side_effect = self.google_side_effect(
            [
                self.get_google_user_error(),  # username is available
                self.create_google_user_success(
                    user.given_name, user.family_name, "/CRI/Test"
                ),  # user created
                self.get_google_user_success(),  # user exists
                self.add_user_alias_success(),  # user alias created
                self.list_google_groups_success([]),  # user groups error
                self.add_user_to_group_error(),  # user is added to group
            ]
        )
        create_google_account(user, "/CRI/Test")
        previous_errors = GoogleSyncErrors.objects.filter(
            google_account__user=user, solved=True
        )
        errors = GoogleSyncErrors.objects.filter(
            google_account__user=user, solved=False
        )
        assert previous_errors.count() == 1
        assert errors.count() == 1
        assert errors[0].on_task == GoogleSyncErrors.OnTaskChoices.SYNC_GROUPS
        assert errors[0].google_group == group
        assert errors[0].google_account == user.google_account
        assert errors[0].retries_count == 0

    @patch("services.google.tasks.create_google_user_task.delay")
    @patch("services.google.interface.GoogleService.service")
    def test_create_google_account_sync_keycloak_error(self, mocked, mocked_delay):
        mocked_delay.side_effect = create_google_user_task
        group = GoogleGroupFactory(organization=self.organization)
        user = UserFactory(
            groups=[self.organization.get_users(), group.people_group.get_members()]
        )
        google_account = GoogleAccount.objects.create(user=user)
        GoogleSyncErrorFactory(
            google_account=google_account,
            on_task=GoogleSyncErrors.OnTaskChoices.KEYCLOAK_USERNAME,
            solved=True,
        )
        mocked.side_effect = self.google_side_effect(
            [
                self.get_google_user_error(),  # username is available
                self.create_google_user_success(
                    user.given_name, user.family_name, "/CRI/Test"
                ),  # user created
                self.get_google_user_success(),  # user exists
                self.add_user_alias_success(),  # user alias created
                self.list_google_groups_success([]),  # user groups are fetched
                self.add_user_to_group_success(),  # user is added to group
            ]
        )
        create_google_account(user, "/CRI/Test")
        previous_errors = GoogleSyncErrors.objects.filter(
            google_account__user=user, solved=True
        )
        errors = GoogleSyncErrors.objects.filter(
            google_account__user=user, solved=False
        )
        assert previous_errors.count() == 1
        assert errors.count() == 1
        assert errors[0].on_task == GoogleSyncErrors.OnTaskChoices.KEYCLOAK_USERNAME
        assert errors[0].google_group is None
        assert errors[0].google_account == user.google_account
        assert errors[0].retries_count == 0


class GoogleUpdateUserErrorTestCase(GoogleTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        superadmin_group = get_superadmins_group()
        cls.user = UserFactory(groups=[superadmin_group])
        cls.organization = OrganizationFactory(code="TEST_GOOGLE_SYNC")

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=self.user)

    @patch("services.google.tasks.update_google_user_task.delay")
    @patch("services.google.interface.GoogleService.service")
    def test_update_google_account_update_error(self, mocked, mocked_delay):
        mocked_delay.side_effect = update_google_user_task
        group = GoogleGroupFactory(organization=self.organization)
        google_account = GoogleAccountFactory(
            groups=[self.organization.get_users(), group.people_group.get_members()]
        )
        GoogleSyncErrorFactory(
            google_account=google_account,
            on_task=GoogleSyncErrors.OnTaskChoices.UPDATE_USER,
            solved=True,
        )
        mocked.side_effect = self.google_side_effect(
            [
                self.update_google_user_error(),  # update user error
                self.list_google_groups_success([]),  # user groups are fetched
                self.add_user_to_group_success(),  # user is added to group
            ]
        )
        update_google_account(google_account.user)
        previous_errors = GoogleSyncErrors.objects.filter(
            google_account=google_account, solved=True
        )
        errors = GoogleSyncErrors.objects.filter(
            google_account=google_account, solved=False
        )
        assert previous_errors.count() == 1
        assert errors.count() == 1
        assert errors[0].on_task == GoogleSyncErrors.OnTaskChoices.UPDATE_USER
        assert errors[0].google_group is None
        assert errors[0].google_account == google_account
        assert errors[0].retries_count == 0

    @patch("services.google.tasks.update_google_user_task.delay")
    @patch("services.google.interface.GoogleService.service")
    def test_update_google_account_sync_groups_error(self, mocked, mocked_delay):
        mocked_delay.side_effect = update_google_user_task
        group = GoogleGroupFactory(organization=self.organization)
        google_account = GoogleAccountFactory(
            groups=[self.organization.get_users(), group.people_group.get_members()]
        )
        GoogleSyncErrorFactory(
            google_account=google_account,
            on_task=GoogleSyncErrors.OnTaskChoices.SYNC_GROUPS,
            solved=True,
        )
        mocked.side_effect = self.google_side_effect(
            [
                self.update_google_user_success(),  # update user
                self.list_google_groups_error(),  # fetch user groups error
            ]
        )
        update_google_account(google_account.user)
        previous_errors = GoogleSyncErrors.objects.filter(
            google_account=google_account, solved=True
        )
        errors = GoogleSyncErrors.objects.filter(
            google_account=google_account, solved=False
        )
        assert previous_errors.count() == 1
        assert errors.count() == 1
        assert errors[0].on_task == GoogleSyncErrors.OnTaskChoices.SYNC_GROUPS
        assert errors[0].google_group is None
        assert errors[0].google_account == google_account
        assert errors[0].retries_count == 0

    @patch("services.google.tasks.update_google_user_task.delay")
    @patch("services.google.interface.GoogleService.service")
    def test_update_google_account_sync_group_error(self, mocked, mocked_delay):
        mocked_delay.side_effect = update_google_user_task
        group = GoogleGroupFactory(organization=self.organization)
        google_account = GoogleAccountFactory(
            groups=[self.organization.get_users(), group.people_group.get_members()]
        )
        GoogleSyncErrorFactory(
            google_account=google_account,
            on_task=GoogleSyncErrors.OnTaskChoices.SYNC_GROUPS,
            solved=True,
        )
        mocked.side_effect = self.google_side_effect(
            [
                self.update_google_user_success(),  # update user
                self.list_google_groups_success([]),  # user groups are fetched
                self.add_user_to_group_error(),  # add user to group error
            ]
        )
        update_google_account(google_account.user)
        previous_errors = GoogleSyncErrors.objects.filter(
            google_account=google_account, solved=True
        )
        errors = GoogleSyncErrors.objects.filter(
            google_account=google_account, solved=False
        )
        assert previous_errors.count() == 1
        assert errors.count() == 1
        assert errors[0].on_task == GoogleSyncErrors.OnTaskChoices.SYNC_GROUPS
        assert errors[0].google_group == group
        assert errors[0].google_account == google_account
        assert errors[0].retries_count == 0


class GoogleSuspendUserErrorTestCase(GoogleTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        superadmin_group = get_superadmins_group()
        cls.user = UserFactory(groups=[superadmin_group])
        cls.organization = OrganizationFactory(code="TEST_GOOGLE_SYNC")

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=self.user)

    @patch("services.google.tasks.suspend_google_user_task.delay")
    @patch("services.google.interface.GoogleService.service")
    def test_suspend_google_account_suspend_error(self, mocked, mocked_delay):
        mocked_delay.side_effect = suspend_google_user_task
        group = GoogleGroupFactory(organization=self.organization)
        google_account = GoogleAccountFactory(
            groups=[self.organization.get_users(), group.people_group.get_members()]
        )
        GoogleSyncErrorFactory(
            google_account=google_account,
            on_task=GoogleSyncErrors.OnTaskChoices.SUSPEND_USER,
            solved=True,
        )
        mocked.side_effect = self.google_side_effect(
            [
                self.update_google_user_error(),  # suspend user error
            ]
        )
        suspend_google_account(google_account.user)
        previous_errors = GoogleSyncErrors.objects.filter(
            google_account=google_account, solved=True
        )
        errors = GoogleSyncErrors.objects.filter(
            google_account=google_account, solved=False
        )
        assert previous_errors.count() == 1
        assert errors.count() == 1
        assert errors[0].on_task == GoogleSyncErrors.OnTaskChoices.SUSPEND_USER
        assert errors[0].google_group is None
        assert errors[0].google_account == google_account


class GoogleCreateGroupErrorTestCase(GoogleTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        superadmin_group = get_superadmins_group()
        cls.user = UserFactory(groups=[superadmin_group])
        cls.organization = OrganizationFactory(code="TEST_GOOGLE_SYNC")

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=self.user)

    @patch("services.google.tasks.create_google_group_task.delay")
    @patch("services.google.interface.GoogleService.service")
    def test_create_google_group_create_error(self, mocked, mocked_delay):
        mocked_delay.side_effect = create_google_group_task
        people_group = PeopleGroupFactory(email="", organization=self.organization)
        google_group = GoogleGroup.objects.create(people_group=people_group)
        GoogleAccountFactory(
            groups=[self.organization.get_users(), people_group.get_members()]
        )
        GoogleSyncErrorFactory(
            google_group=google_group,
            on_task=GoogleSyncErrors.OnTaskChoices.CREATE_GROUP,
            solved=True,
        )
        GoogleSyncErrorFactory(
            google_group=google_group,
            on_task=GoogleSyncErrors.OnTaskChoices.GROUP_ALIAS,
            solved=True,
        )
        GoogleSyncErrorFactory(
            google_group=google_group,
            on_task=GoogleSyncErrors.OnTaskChoices.SYNC_MEMBERS,
            solved=True,
        )
        mocked.side_effect = self.google_side_effect(
            [
                self.get_google_group_error(404),  # email available
                self.create_google_group_error(),  # create group error
            ]
        )
        create_google_group(people_group)
        previous_errors = GoogleSyncErrors.objects.filter(
            google_group=google_group, solved=True
        )
        errors = GoogleSyncErrors.objects.filter(
            google_group=google_group, solved=False
        )
        assert previous_errors.count() == 3
        assert errors.count() == 3
        assert [e.on_task for e in errors.order_by("created_at")] == [
            GoogleSyncErrors.OnTaskChoices.CREATE_GROUP,
            GoogleSyncErrors.OnTaskChoices.GROUP_ALIAS,
            GoogleSyncErrors.OnTaskChoices.SYNC_MEMBERS,
        ]
        assert all(e.google_account is None for e in errors)
        assert all(e.google_group == google_group for e in errors)
        assert all(e.retries_count == 0 for e in errors)

    @patch("services.google.tasks.create_google_group_task.delay")
    @patch("services.google.interface.GoogleService.service")
    def test_create_google_group_alias_error(self, mocked, mocked_delay):
        mocked_delay.side_effect = create_google_group_task
        people_group = PeopleGroupFactory(email="", organization=self.organization)
        google_group = GoogleGroup.objects.create(people_group=people_group)
        GoogleAccountFactory(
            groups=[self.organization.get_users(), people_group.get_members()]
        )
        GoogleSyncErrorFactory(
            google_group=google_group,
            on_task=GoogleSyncErrors.OnTaskChoices.GROUP_ALIAS,
            solved=True,
        )
        mocked.side_effect = self.google_side_effect(
            [
                self.get_google_group_error(404),  # email available
                self.create_google_group_success(),  # create group
                self.add_group_alias_error(),  # group alias error
                self.list_group_members_success([]),  # group members are fetched
                self.add_user_to_group_success(),  # user is added to group
            ]
        )
        create_google_group(people_group)
        previous_errors = GoogleSyncErrors.objects.filter(
            google_group=google_group, solved=True
        )
        errors = GoogleSyncErrors.objects.filter(
            google_group=google_group, solved=False
        )
        assert previous_errors.count() == 1
        assert errors.count() == 1
        assert errors[0].on_task == GoogleSyncErrors.OnTaskChoices.GROUP_ALIAS
        assert errors[0].google_account is None
        assert errors[0].google_group == google_group
        assert errors[0].retries_count == 0

    @patch("services.google.tasks.create_google_group_task.delay")
    @patch("services.google.interface.GoogleService.service")
    def test_create_google_group_sync_members_error(self, mocked, mocked_delay):
        mocked_delay.side_effect = create_google_group_task
        people_group = PeopleGroupFactory(email="", organization=self.organization)
        google_group = GoogleGroup.objects.create(people_group=people_group)
        GoogleAccountFactory(
            groups=[self.organization.get_users(), people_group.get_members()]
        )
        GoogleSyncErrorFactory(
            google_group=google_group,
            on_task=GoogleSyncErrors.OnTaskChoices.SYNC_MEMBERS,
            solved=True,
        )
        mocked.side_effect = self.google_side_effect(
            [
                self.get_google_group_error(404),  # email available
                self.create_google_group_success(),  # create group
                self.add_group_alias_success(),  # group alias
                self.list_group_members_error(),  # group members are fetched
            ]
        )
        create_google_group(people_group)
        previous_errors = GoogleSyncErrors.objects.filter(
            google_group=google_group, solved=True
        )
        errors = GoogleSyncErrors.objects.filter(
            google_group=google_group, solved=False
        )
        assert previous_errors.count() == 1
        assert errors.count() == 1
        assert errors[0].on_task == GoogleSyncErrors.OnTaskChoices.SYNC_MEMBERS
        assert errors[0].google_account is None
        assert errors[0].google_group == google_group
        assert errors[0].retries_count == 0

    @patch("services.google.tasks.create_google_group_task.delay")
    @patch("services.google.interface.GoogleService.service")
    def test_create_google_group_sync_member_error(self, mocked, mocked_delay):
        mocked_delay.side_effect = create_google_group_task
        people_group = PeopleGroupFactory(email="", organization=self.organization)
        google_group = GoogleGroup.objects.create(people_group=people_group)
        google_account = GoogleAccountFactory(
            groups=[self.organization.get_users(), people_group.get_members()]
        )
        GoogleSyncErrorFactory(
            google_group=google_group,
            on_task=GoogleSyncErrors.OnTaskChoices.SYNC_MEMBERS,
            solved=True,
        )
        mocked.side_effect = self.google_side_effect(
            [
                self.get_google_group_error(404),  # email available
                self.create_google_group_success(),  # create group
                self.add_group_alias_success(),  # group alias
                self.list_group_members_success([]),  # group members are fetched
                self.add_user_to_group_error(),  # user is added to group
            ]
        )
        create_google_group(people_group)
        previous_errors = GoogleSyncErrors.objects.filter(
            google_group=google_group, solved=True
        )
        errors = GoogleSyncErrors.objects.filter(
            google_group=google_group, solved=False
        )
        assert previous_errors.count() == 1
        assert errors.count() == 1
        assert errors[0].on_task == GoogleSyncErrors.OnTaskChoices.SYNC_MEMBERS
        assert errors[0].google_account == google_account
        assert errors[0].google_group == google_group
        assert errors[0].retries_count == 0


class GoogleUpdateGroupErrorTestCase(GoogleTestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        superadmin_group = get_superadmins_group()
        cls.user = UserFactory(groups=[superadmin_group])
        cls.organization = OrganizationFactory(code="TEST_GOOGLE_SYNC")

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=self.user)

    @patch("services.google.tasks.update_google_group_task.delay")
    @patch("services.google.interface.GoogleService.service")
    def test_update_google_group_update_error(self, mocked, mocked_delay):
        mocked_delay.side_effect = update_google_group_task
        google_group = GoogleGroupFactory(organization=self.organization)
        GoogleSyncErrorFactory(
            google_group=google_group,
            on_task=GoogleSyncErrors.OnTaskChoices.UPDATE_GROUP,
            solved=True,
        )
        mocked.side_effect = self.google_side_effect(
            [
                self.update_google_group_error(),  # update group error
                self.list_group_members_success([]),  # group members are fetched
                self.add_user_to_group_success(),  # user is added to group
            ]
        )
        update_google_group(google_group.people_group)
        previous_errors = GoogleSyncErrors.objects.filter(
            google_group=google_group, solved=True
        )
        errors = GoogleSyncErrors.objects.filter(
            google_group=google_group, solved=False
        )
        assert previous_errors.count() == 1
        assert errors.count() == 1
        assert errors[0].on_task == GoogleSyncErrors.OnTaskChoices.UPDATE_GROUP
        assert errors[0].google_account is None
        assert errors[0].google_group == google_group
        assert errors[0].retries_count == 0

    @patch("services.google.tasks.update_google_group_task.delay")
    @patch("services.google.interface.GoogleService.service")
    def test_update_google_group_sync_members_error(self, mocked, mocked_delay):
        mocked_delay.side_effect = update_google_group_task
        google_group = GoogleGroupFactory(organization=self.organization)
        GoogleAccountFactory(
            groups=[
                self.organization.get_users(),
                google_group.people_group.get_members(),
            ]
        )
        GoogleSyncErrorFactory(
            google_group=google_group,
            on_task=GoogleSyncErrors.OnTaskChoices.SYNC_MEMBERS,
            solved=True,
        )
        mocked.side_effect = self.google_side_effect(
            [
                self.update_google_group_success(),  # update group
                self.list_group_members_error(),  # group members are fetched
            ]
        )
        update_google_group(google_group.people_group)
        previous_errors = GoogleSyncErrors.objects.filter(
            google_group=google_group, solved=True
        )
        errors = GoogleSyncErrors.objects.filter(
            google_group=google_group, solved=False
        )
        assert previous_errors.count() == 1
        assert errors.count() == 1
        assert errors[0].on_task == GoogleSyncErrors.OnTaskChoices.SYNC_MEMBERS
        assert errors[0].google_account is None
        assert errors[0].google_group == google_group
        assert errors[0].retries_count == 0

    @patch("services.google.tasks.update_google_group_task.delay")
    @patch("services.google.interface.GoogleService.service")
    def test_update_google_group_sync_member_error(self, mocked, mocked_delay):
        mocked_delay.side_effect = update_google_group_task
        google_group = GoogleGroupFactory(organization=self.organization)
        google_account = GoogleAccountFactory(
            groups=[
                self.organization.get_users(),
                google_group.people_group.get_members(),
            ]
        )
        GoogleSyncErrorFactory(
            google_group=google_group,
            on_task=GoogleSyncErrors.OnTaskChoices.SYNC_MEMBERS,
            solved=True,
        )
        mocked.side_effect = self.google_side_effect(
            [
                self.update_google_group_success(),  # update group
                self.list_group_members_success([]),  # group members are fetched
                self.add_user_to_group_error(),  # user is added to group
            ]
        )
        update_google_group(google_group.people_group)
        previous_errors = GoogleSyncErrors.objects.filter(
            google_group=google_group, solved=True
        )
        errors = GoogleSyncErrors.objects.filter(
            google_group=google_group, solved=False
        )
        assert previous_errors.count() == 1
        assert errors.count() == 1
        assert errors[0].on_task == GoogleSyncErrors.OnTaskChoices.SYNC_MEMBERS
        assert errors[0].google_account == google_account
        assert errors[0].google_group == google_group
        assert errors[0].retries_count == 0