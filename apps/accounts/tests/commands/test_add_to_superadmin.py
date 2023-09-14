import io
import uuid

from django.core.management import CommandError, call_command
from django.test import TestCase

from apps.accounts.factories import UserFactory
from apps.accounts.utils import get_superadmins_group


class AddToSuperadminTestCase(TestCase):
    def test_no_argument(self):
        with self.assertRaises(CommandError):
            call_command("add_to_superadmin")

    def test_too_many_argument(self):
        with self.assertRaises(CommandError):
            call_command("add_to_superadmin", keycloak_id="x", people_id="y")

    def test_unknown_identifier(self):
        with self.assertRaises(CommandError):
            call_command("add_to_superadmin", keycloak_id=str(uuid.uuid4()))

    def test_through_keycloak_id(self):
        user = UserFactory()
        with io.StringIO() as f:
            call_command("add_to_superadmin", keycloak_id=user.keycloak_id, stdout=f)
        self.assertIn(user, get_superadmins_group().users.all())

    def test_through_people_id(self):
        user = UserFactory()
        with io.StringIO() as f:
            call_command("add_to_superadmin", people_id=user.people_id, stdout=f)
        self.assertIn(user, get_superadmins_group().users.all())

    def test_through_email(self):
        user = UserFactory()
        with io.StringIO() as f:
            call_command("add_to_superadmin", email=user.email, stdout=f)
        self.assertIn(user, get_superadmins_group().users.all())
