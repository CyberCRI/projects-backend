from django.urls import reverse
from faker import Faker

from apps.accounts.factories import UserFactory
from apps.accounts.models import PrivacySettings
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase

fake = Faker()


class NotificationSettingsViewSetTestCaseAnonymous(JwtAPITestCase):
    def test_retrieve_anonymous(self):
        user = UserFactory(publication_status=PrivacySettings.PrivacyChoices.HIDE)
        response = self.client.get(
            reverse("NotificationSettings-detail", args=(user.keycloak_id,))
        )
        self.assertEqual(response.status_code, 404, response.content)

    def test_update_anonymous(self):
        user = UserFactory()
        payload = {"notify_added_to_project": True}
        response = self.client.put(
            reverse("NotificationSettings-detail", args=(user.keycloak_id,)),
            data=payload,
        )
        self.assertEqual(response.status_code, 401, response.content)

    def test_partial_update_anonymous(self):
        user = UserFactory()
        payload = {"notify_added_to_project": True}
        response = self.client.patch(
            reverse("NotificationSettings-detail", args=(user.keycloak_id,)),
            data=payload,
        )
        self.assertEqual(response.status_code, 401, response.content)


class NotificationSettingsViewSetTestCaseUser(JwtAPITestCase):
    def test_retrieve_self(self):
        user = UserFactory()
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("NotificationSettings-detail", args=[user.keycloak_id])
        )
        assert response.status_code == 200

    def test_retrieve_other(self):
        user = UserFactory(publication_status=PrivacySettings.PrivacyChoices.HIDE)
        self.client.force_authenticate(UserFactory())
        response = self.client.get(
            reverse("NotificationSettings-detail", args=[user.keycloak_id])
        )
        assert response.status_code == 404

    def test_update_self(self):
        user = UserFactory()
        data = {
            "notify_added_to_project": fake.boolean(),
            "announcement_published": fake.boolean(),
            "followed_project_has_been_edited": fake.boolean(),
            "project_has_been_commented": fake.boolean(),
            "project_has_been_edited": fake.boolean(),
            "project_ready_for_review": fake.boolean(),
            "project_has_been_reviewed": fake.boolean(),
        }
        self.client.force_authenticate(user)
        response = self.client.put(
            reverse("NotificationSettings-detail", args=[user.keycloak_id]),
            data=data,
        )
        assert response.status_code == 200
        user.notification_settings.refresh_from_db()
        assert (
            user.notification_settings.notify_added_to_project
            == data["notify_added_to_project"]
        )
        assert (
            user.notification_settings.announcement_published
            == data["announcement_published"]
        )
        assert (
            user.notification_settings.followed_project_has_been_edited
            == data["followed_project_has_been_edited"]
        )
        assert (
            user.notification_settings.project_has_been_commented
            == data["project_has_been_commented"]
        )
        assert (
            user.notification_settings.project_has_been_edited
            == data["project_has_been_edited"]
        )
        assert (
            user.notification_settings.project_ready_for_review
            == data["project_ready_for_review"]
        )
        assert (
            user.notification_settings.project_has_been_reviewed
            == data["project_has_been_reviewed"]
        )

    def test_update_other(self):
        user = UserFactory()
        payload = {"notify_added_to_project": True}
        self.client.force_authenticate(UserFactory())
        response = self.client.put(
            reverse("NotificationSettings-detail", args=[user.keycloak_id]),
            data=payload,
        )
        assert response.status_code == 403

    def test_partial_update_self(self):
        user = UserFactory()
        payload = {"notify_added_to_project": True}
        self.client.force_authenticate(user)
        response = self.client.patch(
            reverse("NotificationSettings-detail", args=[user.keycloak_id]),
            data=payload,
        )
        self.assertEqual(response.status_code, 200, response.content)
        user.notification_settings.refresh_from_db()
        self.assertTrue(user.notification_settings.notify_added_to_project)


class NotificationSettingsViewSetTestCaseSuperAdmin(JwtAPITestCase):
    def test_retrieve_superadmin_self(self):
        user = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("NotificationSettings-detail", args=(user.keycloak_id,))
        )
        self.assertEqual(response.status_code, 200, response.content)

    def test_retrieve_superadmin_other(self):
        user = UserFactory(publication_status=PrivacySettings.PrivacyChoices.HIDE)
        self.client.force_authenticate(UserFactory(groups=[get_superadmins_group()]))
        response = self.client.get(
            reverse("NotificationSettings-detail", args=(user.keycloak_id,))
        )
        self.assertEqual(response.status_code, 200, response.content)

    def test_update_superadmin_self(self):
        admin = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(admin)
        payload = {"notify_added_to_project": False}
        self.assertTrue(admin.notification_settings.notify_added_to_project)
        response = self.client.put(
            reverse("NotificationSettings-detail", args=(admin.keycloak_id,)),
            data=payload,
        )
        self.assertEqual(response.status_code, 200, response.content)
        admin.notification_settings.refresh_from_db()
        self.assertFalse(admin.notification_settings.notify_added_to_project)

    def test_update_superadmin_other(self):
        user = UserFactory()
        admin = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(admin)
        payload = {"notify_added_to_project": False}
        self.assertTrue(user.notification_settings.notify_added_to_project)
        response = self.client.put(
            reverse("NotificationSettings-detail", args=(user.keycloak_id,)),
            data=payload,
        )
        self.assertEqual(response.status_code, 200, response.content)
        user.notification_settings.refresh_from_db()
        self.assertFalse(user.notification_settings.notify_added_to_project)

    def test_partial_update_superadmin_self(self):
        admin = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(admin)
        payload = {"notify_added_to_project": False}
        self.assertTrue(admin.notification_settings.notify_added_to_project)
        response = self.client.patch(
            reverse("NotificationSettings-detail", args=(admin.keycloak_id,)),
            data=payload,
        )
        self.assertEqual(response.status_code, 200, response.content)
        admin.notification_settings.refresh_from_db()
        self.assertFalse(admin.notification_settings.notify_added_to_project)

    def test_partial_update_superadmin_other(self):
        user = UserFactory()
        admin = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(admin)
        payload = {"notify_added_to_project": False}
        self.assertTrue(user.notification_settings.notify_added_to_project)
        response = self.client.patch(
            reverse("NotificationSettings-detail", args=(user.keycloak_id,)),
            data=payload,
        )
        self.assertEqual(response.status_code, 200, response.content)
        user.notification_settings.refresh_from_db()
        self.assertFalse(user.notification_settings.notify_added_to_project)
