import time
import uuid
from unittest.mock import patch

from django.conf import settings
from django.urls import reverse

from apps.accounts.factories import PeopleGroupFactory, SeedUserFactory, UserFactory
from apps.accounts.models import PeopleGroup, ProjectUser
from apps.accounts.utils import get_superadmins_group
from apps.commons.test.mixins import skipUnlessGoogle
from apps.commons.test.testcases import JwtAPITestCase
from apps.organizations.factories import OrganizationFactory
from keycloak import KeycloakGetError
from services.google.factories import GoogleGroupFactory, GoogleUserFactory
from services.google.interface import GoogleService
from services.google.tasks import (
    create_google_group_task,
    create_google_user_task,
    suspend_google_user_task,
    update_google_group_task,
    update_google_user_task,
)
from services.keycloak.interface import KeycloakService


#@skipUnlessGoogle
class GoogleServiceTestCase(JwtAPITestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        superadmin_group = get_superadmins_group()
        cls.user = UserFactory(groups=[superadmin_group])
        cls.organization = OrganizationFactory(code="TEST_GOOGLE_SYNC")

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=self.user)

    def tearDown(self):
        for user in ProjectUser.objects.filter(given_name="googlesync"):
            GoogleService.delete_user(user)
            try:
                KeycloakService.get_user(user.keycloak_id)
                KeycloakService.delete_user(user)
            except KeycloakGetError:
                pass
        for group in PeopleGroup.objects.filter(name__startswith="googlesync"):
            GoogleService.delete_group(group)
        return super().tearDown()

    @classmethod
    def create_user_payload(cls, **kwargs):
        unique_id = uuid.uuid4()
        return {
            "personal_email": kwargs.get(
                "personal_email",
                f"test.googlesync.personal.{unique_id}@yopmail.com",
            ),
            "email": kwargs.get("email", f"test.googlesync.{unique_id}@yopmail.com"),
            "given_name": "googlesync",
            "family_name": f"test{unique_id}",
            "roles_to_add": kwargs.get(
                "roles_to_add", [cls.organization.get_users().name]
            ),
            "create_in_google": kwargs.get("create_in_google", True),
            "main_google_group": kwargs.get("google_main_group", "Test Google Sync"),
        }

    @classmethod
    def create_group_payload(cls, **kwargs):
        return {
            "name": f"googlesync-{uuid.uuid4()}",
            "organization": kwargs.get("organization", cls.organization.id),
            "create_in_google": kwargs.get("create_in_google", True),
            "email": kwargs.get("email", ""),
            "type": kwargs.get("type", "group"),
            "description": kwargs.get("description", "description"),
        }

    @patch("services.google.tasks.create_google_user_task.delay")
    def test_create_user(self, mocked):
        mocked.side_effect = create_google_user_task
        payload = self.create_user_payload()
        response = self.client.post(reverse("ProjectUser-list"), data=payload)
        content = response.json()
        assert response.status_code == 201
        content = response.json()
        google_user = GoogleService.get_user(content["email"], 5)
        projects_user = ProjectUser.objects.get(keycloak_id=content["keycloak_id"])
        keycloak_user = KeycloakService.get_user(content["keycloak_id"])
        assert google_user is not None
        assert (
            projects_user.email
            == google_user["primaryEmail"]
            == keycloak_user["username"]
            == content["email"]
        )
        assert (
            projects_user.personal_email
            == payload["email"]
            == keycloak_user["email"]
            == content["personal_email"]
        )
        # wait for propagation
        alias = projects_user.email.replace(
            settings.GOOGLE_EMAIL_DOMAIN, settings.GOOGLE_EMAIL_ALIAS_DOMAIN
        )
        for _ in range(30):
            google_user = GoogleService.get_user(projects_user.email, 5)
            emails = [email["address"] for email in google_user["emails"]]
            if alias not in emails:
                time.sleep(2)
            else:
                break
        emails = [email["address"] for email in google_user["emails"]]
        assert alias in emails

    @patch("services.google.tasks.create_google_user_task.delay")
    def test_create_user_in_group(self, mocked):
        mocked.side_effect = create_google_user_task
        people_group = GoogleGroupFactory(organization=self.organization)
        payload = self.create_user_payload(
            roles_to_add=[
                people_group.get_members().name,
                self.organization.get_users().name,
            ]
        )
        response = self.client.post(reverse("ProjectUser-list"), data=payload)
        assert response.status_code == 201
        content = response.json()
        google_user = GoogleService.get_user(content["email"], 5)
        projects_user = ProjectUser.objects.get(keycloak_id=content["keycloak_id"])
        keycloak_user = KeycloakService.get_user(content["keycloak_id"])
        assert google_user is not None
        assert (
            projects_user.email
            == google_user["primaryEmail"]
            == keycloak_user["username"]
            == content["email"]
        )
        assert (
            projects_user.personal_email
            == payload["email"]
            == keycloak_user["email"]
            == content["personal_email"]
        )
        # wait for propagation
        for _ in range(30):
            user_groups = GoogleService.get_user_groups(projects_user)
            if len(user_groups) != 1:
                time.sleep(2)
            else:
                break
        assert len(user_groups) == 1
        assert user_groups[0]["email"] == people_group.email

    @patch("services.google.tasks.create_google_user_task.delay")
    def test_create_account_for_existing_user(self, mocked):
        mocked.side_effect = create_google_user_task
        people_group = GoogleGroupFactory(organization=self.organization)
        user_data = self.create_user_payload()
        projects_user = SeedUserFactory(
            personal_email=user_data["personal_email"],
            email=user_data["email"],
            given_name=user_data["given_name"],
            family_name=user_data["family_name"],
        )
        projects_user.groups.add(
            self.organization.get_users(), people_group.get_members()
        )
        payload = {"create_in_google": True, "main_google_group": "Test Google Sync"}
        response = self.client.patch(
            reverse("ProjectUser-detail", args=(projects_user.keycloak_id,)),
            data=payload,
        )
        assert response.status_code == 200
        content = response.json()
        google_user = GoogleService.get_user(content["email"], 5)
        keycloak_user = KeycloakService.get_user(content["keycloak_id"])
        projects_user.refresh_from_db()
        assert google_user is not None
        assert (
            projects_user.email
            == google_user["primaryEmail"]
            == keycloak_user["username"]
            == content["email"]
        )
        assert (
            projects_user.personal_email
            == user_data["email"]
            == keycloak_user["email"]
            == content["personal_email"]
        )
        # wait for propagation
        for _ in range(30):
            user_groups = GoogleService.get_user_groups(projects_user)
            if len(user_groups) != 1:
                time.sleep(2)
            else:
                break
        assert len(user_groups) == 1
        assert user_groups[0]["email"] == people_group.email

    @patch("services.google.tasks.create_google_user_task.delay")
    def test_create_user_email_increment(self, mocked):
        mocked.side_effect = create_google_user_task
        payload = self.create_user_payload()
        payload_1 = {
            **payload,
            "personal_email": ".1@".join(payload["personal_email"].split("@")),
            "email": ".1@".join(payload["email"].split("@")),
        }
        payload_2 = {
            **payload,
            "personal_email": ".2@".join(payload["personal_email"].split("@")),
            "email": ".2@".join(payload["email"].split("@")),
        }
        response_1 = self.client.post(reverse("ProjectUser-list"), data=payload_1)
        response_2 = self.client.post(reverse("ProjectUser-list"), data=payload_2)
        assert response_1.status_code == 201
        assert response_2.status_code == 201
        content_1 = response_1.json()
        content_2 = response_2.json()
        for _ in range(30):
            google_user_1 = GoogleService.get_user(content_1["email"], 5)
            google_user_2 = GoogleService.get_user(content_2["email"], 5)
            if not google_user_1 or not google_user_2:
                time.sleep(2)
            else:
                break
        assert google_user_1 is not None
        assert google_user_2 is not None
        assert ".1@".join(content_1["email"].split("@")) == content_2["email"]

    @patch("services.google.tasks.create_google_group_task.delay")
    def test_create_group_with_email(self, mocked):
        mocked.side_effect = create_google_group_task
        payload = self.create_group_payload(
            email=f"team.googlesync.email@{settings.GOOGLE_EMAIL_DOMAIN}"
        )
        response = self.client.post(
            reverse("PeopleGroup-list", args=(self.organization.code,)), data=payload
        )
        assert response.status_code == 201
        content = response.json()
        for _ in range(30):
            google_group = GoogleService.get_group(content["email"], 5)
            if not google_group:
                time.sleep(2)
            else:
                break
        projects_group = PeopleGroup.objects.get(id=response.json()["id"])
        assert google_group is not None
        assert projects_group.email == google_group["email"] == payload["email"]

    @patch("services.google.tasks.update_google_group_task.delay")
    def test_update_group_existing_email(self, mocked):
        mocked.side_effect = update_google_group_task
        group_1 = GoogleGroupFactory(organization=self.organization)
        group_2 = PeopleGroupFactory(organization=self.organization)
        payload = {"email": group_1.email}
        response = self.client.patch(
            reverse("PeopleGroup-detail", args=(self.organization.code, group_2.id)),
            data=payload,
        )
        assert response.status_code == 409
        assert response.json() == {
            "detail": "This email is already used by another group"
        }
        group_1.refresh_from_db()
        group_2.refresh_from_db()
        assert group_1.email != group_2.email

    @patch("services.google.tasks.update_google_user_task.delay")
    def test_update_user_existing_email(self, mocked):
        mocked.side_effect = update_google_user_task
        user_1 = GoogleUserFactory(groups=[self.organization.get_users()])
        # Delete user in Keycloak or it will throw an error before Google
        KeycloakService.delete_user(user_1)
        user_2 = SeedUserFactory(groups=[self.organization.get_users()])
        payload = {"email": user_1.email}
        response = self.client.patch(
            reverse("ProjectUser-detail", args=(user_2.keycloak_id,)),
            data=payload,
        )
        assert response.status_code == 409
        assert response.json() == {
            "detail": "This email is already used by another user"
        }
        user_1.refresh_from_db()
        user_2.refresh_from_db()
        # Google sync is made outside of atomic block, so db transaction is not cancelled
        assert user_1.email == user_2.email

    @patch("services.google.tasks.create_google_group_task.delay")
    def test_create_group_without_email(self, mocked):
        mocked.side_effect = create_google_group_task
        payload = self.create_group_payload()
        response = self.client.post(
            reverse("PeopleGroup-list", args=(self.organization.code,)), data=payload
        )
        assert response.status_code == 201
        content = response.json()
        for _ in range(30):
            google_group = GoogleService.get_group(content["email"], 5)
            if not google_group:
                time.sleep(2)
            else:
                break
        projects_group = PeopleGroup.objects.get(id=response.json()["id"])
        assert google_group is not None
        assert projects_group.email == google_group["email"]

    @patch("services.google.tasks.create_google_group_task.delay")
    def test_create_group_for_existing_group(self, mocked):
        mocked.side_effect = create_google_group_task
        group_data = self.create_group_payload()
        projects_group = PeopleGroupFactory(
            name=group_data["name"],
            description=group_data["description"],
            email=group_data["email"],
            type=group_data["type"],
            organization=self.organization,
        )
        payload = {"create_in_google": True}
        response = self.client.patch(
            reverse(
                "PeopleGroup-detail", args=(self.organization.code, projects_group.id)
            ),
            data=payload,
        )
        assert response.status_code == 200
        content = response.json()
        for _ in range(30):
            google_group = GoogleService.get_group(content["email"], 5)
            if google_group["name"] != projects_group.name:
                time.sleep(2)
            else:
                break
        assert google_group is not None
        assert content["email"] == google_group["email"]

    @patch("services.google.tasks.update_google_group_task.delay")
    def test_add_user_to_group(self, mocked):
        mocked.side_effect = update_google_group_task
        people_group = GoogleGroupFactory(organization=self.organization)
        user = GoogleUserFactory(groups=[self.organization.get_users()])
        payload = {
            PeopleGroup.DefaultGroup.MEMBERS: [user.keycloak_id],
        }
        response = self.client.post(
            reverse(
                "PeopleGroup-add-member",
                args=(self.organization.code, people_group.pk),
            ),
            payload,
        )
        assert response.status_code == 204
        # wait for propagation
        for _ in range(30):
            user_groups = GoogleService.get_user_groups(user)
            if len(user_groups) != 1:
                time.sleep(2)
            else:
                break
        assert len(user_groups) == 1
        assert user_groups[0]["email"] == people_group.email

    @patch("services.google.tasks.update_google_group_task.delay")
    def test_remove_user_from_group(self, mocked):
        mocked.side_effect = update_google_group_task
        people_group = GoogleGroupFactory(organization=self.organization)
        user = GoogleUserFactory(groups=[self.organization.get_users()])
        GoogleService.add_user_to_group(user, people_group)
        for _ in range(30):
            user_groups = GoogleService.get_user_groups(user)
            if len(user_groups) != 1:
                time.sleep(2)
            else:
                break
        payload = {
            "users": [user.keycloak_id],
        }
        response = self.client.post(
            reverse(
                "PeopleGroup-remove-member",
                args=(self.organization.code, people_group.pk),
            ),
            payload,
        )
        assert response.status_code == 204
        # wait for propagation
        for _ in range(30):
            user_groups = GoogleService.get_user_groups(user)
            if len(user_groups) != 0:
                time.sleep(2)
            else:
                break
        assert len(user_groups) == 0

    @patch("services.google.tasks.update_google_user_task.delay")
    def test_update_user(self, mocked):
        mocked.side_effect = update_google_user_task
        user = GoogleUserFactory(groups=[self.organization.get_users()])
        payload = {
            "family_name": "test_update",
        }
        response = self.client.patch(
            reverse("ProjectUser-detail", args=(user.keycloak_id,)),
            data=payload,
        )
        assert response.status_code == 200
        content = response.json()
        for _ in range(30):
            google_user = GoogleService.get_user(user.email, 5)
            if not google_user or google_user["name"]["familyName"] != "test_update":
                time.sleep(2)
            else:
                break
        assert google_user is not None
        user.refresh_from_db()
        assert (
            user.family_name
            == google_user["name"]["familyName"]
            == "test_update"
            == content["family_name"]
        )

    @patch("services.google.tasks.update_google_user_task.delay")
    def test_update_user_main_group(self, mocked):
        mocked.side_effect = update_google_user_task
        user = GoogleUserFactory(groups=[self.organization.get_users()])
        payload = {
            "main_google_group": "Test Google Sync Update",
        }
        response = self.client.patch(
            reverse("ProjectUser-detail", args=(user.keycloak_id,)),
            data=payload,
        )
        assert response.status_code == 200
        for _ in range(30):
            google_user = GoogleService.get_user(user.email, 5)
            if google_user["orgUnitPath"] != "/CRI/Test Google Sync Update":
                time.sleep(2)
            else:
                break
        assert google_user["orgUnitPath"] == "/CRI/Test Google Sync Update"

    @patch("services.google.tasks.update_google_group_task.delay")
    def test_update_group(self, mocked):
        mocked.side_effect = update_google_group_task
        group = GoogleGroupFactory(organization=self.organization)
        payload = {
            "name": "test_update",
        }
        response = self.client.patch(
            reverse(
                "PeopleGroup-detail",
                args=(self.organization.code, group.id),
            ),
            data=payload,
        )
        assert response.status_code == 200
        for _ in range(30):
            google_group = GoogleService.get_group(group.email, 5)
            if google_group["name"] != "test_update":
                time.sleep(2)
            else:
                break
        assert google_group["name"] == "test_update"

    @patch("services.google.tasks.update_google_group_task.delay")
    def test_update_group_members(self, mocked):
        mocked.side_effect = update_google_group_task
        group = GoogleGroupFactory(organization=self.organization)
        users = UserFactory.create_batch(3)
        org_users = UserFactory.create_batch(3, groups=[self.organization.get_users()])
        google_users = GoogleUserFactory.create_batch(
            3, groups=[self.organization.get_users()]
        )

        payload = {
            PeopleGroup.DefaultGroup.MEMBERS: [
                users[0].keycloak_id,
                org_users[0].keycloak_id,
                google_users[0].keycloak_id,
            ],
            PeopleGroup.DefaultGroup.MANAGERS: [
                users[1].keycloak_id,
                org_users[1].keycloak_id,
                google_users[1].keycloak_id,
            ],
            PeopleGroup.DefaultGroup.LEADERS: [
                users[2].keycloak_id,
                org_users[2].keycloak_id,
                google_users[2].keycloak_id,
            ],
        }
        response = self.client.post(
            reverse(
                "PeopleGroup-add-member",
                args=(self.organization.code, group.pk),
            ),
            payload,
        )
        assert response.status_code == 204
        # wait for propagation
        for _ in range(30):
            group_members = GoogleService.get_group_members(group)
            if len(group_members) != 3:
                time.sleep(2)
            else:
                break
        assert len(group_members) == 3
        assert {
            group_members[0]["email"],
            group_members[1]["email"],
            group_members[2]["email"],
        } == {user.email for user in google_users}

    @patch("services.google.tasks.suspend_google_user_task.delay")
    def test_delete_user(self, mocked):
        mocked.side_effect = suspend_google_user_task
        user = GoogleUserFactory(groups=[self.organization.get_users()])
        response = self.client.delete(
            reverse("ProjectUser-detail", args=(user.keycloak_id,))
        )
        assert response.status_code == 204
        for _ in range(30):
            google_user = GoogleService.get_user(user.email, 5)
            if not google_user["suspended"] is True:
                time.sleep(2)
            else:
                break
        assert google_user["suspended"] is True
        GoogleService.delete_user(user)  # cleanup

    @patch("services.google.tasks.suspend_google_user_task.delay")
    def test_delete_user_not_in_google(self, mocked):
        mocked.side_effect = suspend_google_user_task
        user = SeedUserFactory(groups=[self.organization.get_users()])
        response = self.client.delete(
            reverse("ProjectUser-detail", args=(user.keycloak_id,))
        )
        assert response.status_code == 204
