from unittest.mock import call, patch

from apps.accounts.factories import UserFactory
from apps.commons.test import JwtAPITestCase
from apps.organizations.factories import OrganizationFactory


class DeleteUserQuerysetsCacheTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()

    @patch("apps.accounts.models.clear_redis_cache_model_method")
    def test_cache_deleted_on_add_role(self, mock_cache):
        user = UserFactory()
        user.groups.add(self.organization.get_users())
        mock_cache.assert_has_calls([call(user, "querysets")])

    @patch("apps.accounts.models.clear_redis_cache_model_method")
    def test_cache_deleted_on_remove_role(self, mock_cache):
        user = UserFactory(groups=[self.organization.get_users()])
        user.groups.remove(self.organization.get_users())
        mock_cache.assert_has_calls([call(user, "querysets"), call(user, "querysets")])

    @patch("apps.accounts.models.clear_redis_cache_model_method")
    def test_cache_deleted_on_set_roles(self, mock_cache):
        user = UserFactory()
        user.groups.set([self.organization.get_users()])
        mock_cache.assert_has_calls([call(user, "querysets")])

    @patch("apps.accounts.models.clear_redis_cache_model_method")
    def test_cache_deleted_on_clear_roles(self, mock_cache):
        user = UserFactory(groups=[self.organization.get_users()])
        user.groups.clear()
        mock_cache.assert_has_calls([call(user, "querysets"), call(user, "querysets")])

    @patch("apps.accounts.models.clear_redis_cache_model_method")
    def test_cache_deleted_on_add_user(self, mock_cache):
        user = UserFactory()
        self.organization.get_users().users.add(user)
        mock_cache.assert_has_calls([call(user, "querysets")])

    @patch("apps.accounts.models.clear_redis_cache_model_method")
    def test_cache_deleted_on_remove_user(self, mock_cache):
        user = UserFactory(groups=[self.organization.get_users()])
        self.organization.get_users().users.remove(user)
        mock_cache.assert_has_calls([call(user, "querysets"), call(user, "querysets")])

    @patch("apps.accounts.models.clear_redis_cache_model_method")
    def test_cache_deleted_on_set_users(self, mock_cache):
        user = UserFactory()
        self.organization.get_users().users.set([user])
        mock_cache.assert_has_calls([call(user, "querysets")])

    @patch("apps.accounts.models.clear_redis_cache_model_method")
    def test_cache_deleted_on_clear_users(self, mock_cache):
        user = UserFactory(groups=[self.organization.get_users()])
        self.organization.get_users().users.clear()
        mock_cache.assert_has_calls([call(user, "querysets"), call(user, "querysets")])
