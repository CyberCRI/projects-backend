from django.urls import reverse
from faker import Faker

from apps.accounts.factories import UserFactory
from apps.accounts.models import PrivacySettings
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase
from apps.organizations.factories import OrganizationFactory

fake = Faker()


class PrivacySettingsTestCaseMixin:
    def get_payload(self):
        return {
            key: fake.enum(PrivacySettings.PrivacyChoices)
            for key in [
                "publication_status",
                "profile_picture",
                "skills",
                "socials",
                "mobile_phone",
                "personal_email",
            ]
        }


class PrivacySettingsViewSetTestCaseAnonymous(
    JwtAPITestCase, PrivacySettingsTestCaseMixin
):
    def test_retrieve_anonymous(self):
        user = UserFactory(publication_status=PrivacySettings.PrivacyChoices.HIDE)
        response = self.client.get(
            reverse("PrivacySettings-detail", args=(user.keycloak_id,))
        )
        assert response.status_code == 404

    def test_partial_update_anonymous(self):
        user = UserFactory()
        payload = self.get_payload()
        response = self.client.patch(
            reverse("PrivacySettings-detail", args=(user.keycloak_id,)),
            data=payload,
        )
        assert response.status_code == 401


class PrivacySettingsViewSetTestCaseUser(JwtAPITestCase, PrivacySettingsTestCaseMixin):
    def test_retrieve_self(self):
        user = UserFactory()
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("PrivacySettings-detail", args=[user.keycloak_id])
        )
        assert response.status_code == 200

    def test_retrieve_other(self):
        user = UserFactory(publication_status=PrivacySettings.PrivacyChoices.HIDE)
        self.client.force_authenticate(UserFactory())
        response = self.client.get(
            reverse("PrivacySettings-detail", args=[user.keycloak_id])
        )
        assert response.status_code == 404

    def test_partial_update_other(self):
        user = UserFactory()
        payload = self.get_payload()
        self.client.force_authenticate(UserFactory())
        response = self.client.patch(
            reverse("PrivacySettings-detail", args=[user.keycloak_id]),
            data=payload,
        )
        assert response.status_code == 403

    def test_partial_update_self(self):
        user = UserFactory()
        payload = self.get_payload()
        self.client.force_authenticate(user)
        response = self.client.patch(
            reverse("PrivacySettings-detail", args=[user.keycloak_id]),
            data=payload,
        )
        assert response.status_code == 200
        for key in payload:
            assert response.data[key] == payload[key]


class PrivacySettingsViewSetTestCaseSuperAdmin(
    JwtAPITestCase, PrivacySettingsTestCaseMixin
):
    def test_retrieve_superadmin_self(self):
        user = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("PrivacySettings-detail", args=(user.keycloak_id,))
        )
        assert response.status_code == 200

    def test_retrieve_superadmin_other(self):
        user = UserFactory()
        admin = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(admin)
        response = self.client.get(
            reverse("PrivacySettings-detail", args=(user.keycloak_id,))
        )
        assert response.status_code == 200

    def test_partial_update_superadmin_self(self):
        admin = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(admin)
        payload = self.get_payload()
        self.assertTrue(admin.notification_settings.notify_added_to_project)
        response = self.client.patch(
            reverse("PrivacySettings-detail", args=(admin.keycloak_id,)),
            data=payload,
        )
        assert response.status_code == 200
        for key in payload:
            assert response.data[key] == payload[key]

    def test_partial_update_superadmin_other(self):
        user = UserFactory()
        admin = UserFactory(groups=[get_superadmins_group()])
        self.client.force_authenticate(admin)
        payload = self.get_payload()
        self.assertTrue(user.notification_settings.notify_added_to_project)
        response = self.client.patch(
            reverse("PrivacySettings-detail", args=(user.keycloak_id,)),
            data=payload,
        )
        assert response.status_code == 200
        for key in payload:
            assert response.data[key] == payload[key]


class PrivacySettingsViewSetTestCaseOrgAdmin(
    JwtAPITestCase, PrivacySettingsTestCaseMixin
):
    def test_retrieve_orgadmin_self(self):
        org_admin = UserFactory()
        organization = OrganizationFactory()
        organization.admins.add(org_admin)
        self.client.force_authenticate(org_admin)
        response = self.client.get(
            reverse("PrivacySettings-detail", args=(org_admin.keycloak_id,))
        )
        assert response.status_code == 200

    def test_retrieve_orgadmin_other(self):
        user = UserFactory(
            publication_status=PrivacySettings.PrivacyChoices.ORGANIZATION
        )
        org_admin = UserFactory()
        organization = OrganizationFactory()
        organization.admins.add(org_admin)
        organization.users.add(user)
        self.client.force_authenticate(org_admin)
        response = self.client.get(
            reverse("PrivacySettings-detail", args=(org_admin.keycloak_id,))
        )
        assert response.status_code == 200

    def test_partial_update_orgadmin_self(self):
        org_admin = UserFactory()
        organization = OrganizationFactory()
        organization.admins.add(org_admin)
        self.client.force_authenticate(org_admin)
        payload = self.get_payload()
        self.assertTrue(org_admin.notification_settings.notify_added_to_project)
        response = self.client.patch(
            reverse("PrivacySettings-detail", args=(org_admin.keycloak_id,)),
            data=payload,
        )
        assert response.status_code == 200
        for key in payload:
            assert response.data[key] == payload[key]

    def test_partial_update_orgadmin_other(self):
        user = UserFactory(
            publication_status=PrivacySettings.PrivacyChoices.ORGANIZATION
        )
        org_admin = UserFactory()
        organization = OrganizationFactory()
        organization.admins.add(org_admin)
        organization.users.add(user)
        self.client.force_authenticate(org_admin)
        payload = self.get_payload()
        self.assertTrue(user.notification_settings.notify_added_to_project)
        response = self.client.patch(
            reverse("PrivacySettings-detail", args=(user.keycloak_id,)),
            data=payload,
        )
        assert response.status_code == 200
        for key in payload:
            assert response.data[key] == payload[key]
