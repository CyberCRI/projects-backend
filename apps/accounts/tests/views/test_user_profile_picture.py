from apps.accounts.factories import UserFactory
from apps.commons.test import ImageStorageTestCaseMixin, JwtAPITestCase


class UserProfilePictureTestCase(JwtAPITestCase, ImageStorageTestCaseMixin):
    list_view = "UserProfilePicture-list"
    detail_view = "UserProfilePicture-detail"
    field_name = "profile_picture"
    base_permissions = ["accounts.change_projectuser"]
    org_permissions = ["organizations.change_projectuser"]

    # Tests for POST calls that should pass
    def test_upload_images_base_permission(self):
        self.create_user(self.base_permissions)
        kwargs = {"user_keycloak_id": UserFactory().keycloak_id}
        self.assert_image_upload(self.list_view, **kwargs)

    def test_upload_images_org_permission(self):
        _, _, organization = self.create_org_user(self.org_permissions)
        user = UserFactory()
        organization.users.add(user)
        kwargs = {"user_keycloak_id": user.keycloak_id}
        self.assert_image_upload(self.list_view, **kwargs)

    def test_upload_images_self(self):
        user = UserFactory()
        self.client.force_authenticate(user)
        kwargs = {"user_keycloak_id": user.keycloak_id}
        self.assert_image_upload(self.list_view, **kwargs)

    # Tests for POST calls that should fail
    def test_upload_oversized_image(self):
        user = UserFactory()
        self.client.force_authenticate(user)
        kwargs = {"user_keycloak_id": user.keycloak_id}
        self.assert_image_too_large(self.list_view, **kwargs)

    def test_upload_images_no_permission(self):
        self.create_user()
        kwargs = {"user_keycloak_id": UserFactory().keycloak_id}
        self.assert_image_upload(self.list_view, **kwargs, denied=True)

    # Tests for DELETE calls that should pass
    def test_delete_fk_images_base_permission(self):
        self.create_user(self.base_permissions)
        user = UserFactory()
        kwargs = {"user_keycloak_id": user.keycloak_id}
        self.assert_delete_fk_image(self.detail_view, self.field_name, user, **kwargs)

    def test_delete_fk_images_org_permission(self):
        _, _, organization = self.create_org_user(self.org_permissions)
        user = UserFactory()
        organization.users.add(user)
        kwargs = {"user_keycloak_id": user.keycloak_id}
        self.assert_delete_fk_image(self.detail_view, self.field_name, user, **kwargs)

    def test_delete_images_self(self):
        user = UserFactory()
        self.client.force_authenticate(user)
        kwargs = {"user_keycloak_id": user.keycloak_id}
        self.assert_delete_fk_image(self.detail_view, self.field_name, user, **kwargs)

    # Tests for DELETE calls that should fail
    def test_delete_fk_images_no_permission(self):
        self.create_user()
        user = UserFactory()
        kwargs = {"user_keycloak_id": user.keycloak_id}
        self.assert_delete_fk_image(
            self.detail_view, self.field_name, user, denied=True, **kwargs
        )
