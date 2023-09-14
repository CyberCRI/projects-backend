from apps.accounts.factories import UserFactory
from apps.accounts.models import ProjectUser
from apps.commons.test import JwtAPITestCase
from apps.notifications.models import NotificationSettings


class SignalsTestCase(JwtAPITestCase):
    def test_create_notification_settings(self):
        self.assertEqual(
            NotificationSettings.objects.count(), ProjectUser.objects.count()
        )
        user = UserFactory()
        self.assertEqual(
            NotificationSettings.objects.count(), ProjectUser.objects.count()
        )
        self.assertEqual(
            NotificationSettings.objects.get(user=user), user.notification_settings
        )
