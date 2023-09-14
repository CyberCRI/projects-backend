from apps.accounts.utils import get_superadmins_group
from apps.commons.test import ImageStorageTestCaseMixin, JwtAPITestCase
from apps.organizations.factories import OrganizationFactory


class FaqImagesTestCase(JwtAPITestCase, ImageStorageTestCaseMixin):
    list_view = "Faq-images-list"
    detail_view = "Faq-images-detail"
    field_name = "images"
    base_permissions = []
    org_permissions = ["organizations.change_faq"]

    # Tests for POST calls that should pass
    def test_upload_images_base_permission(self):
        user = self.create_user(self.base_permissions)
        user.groups.add(get_superadmins_group())
        organization = OrganizationFactory()
        kwargs = {"organization_code": organization.code}
        self.assert_image_upload(self.list_view, **kwargs)

    def test_upload_images_org_permission(self):
        _, _, organization = self.create_org_user(self.org_permissions)
        kwargs = {"organization_code": organization.code}
        self.assert_image_upload(self.list_view, **kwargs)

    # Tests for POST calls that should fail
    def test_upload_oversized_image(self):
        user = self.create_user(self.base_permissions)
        user.groups.add(get_superadmins_group())
        organization = OrganizationFactory()
        kwargs = {"organization_code": organization.code}
        self.assert_image_too_large(self.list_view, **kwargs)

    def test_upload_images_no_permission(self):
        self.create_user()
        organization = OrganizationFactory()
        kwargs = {"organization_code": organization.code}
        self.assert_image_upload(self.list_view, denied=True, **kwargs)

    # Tests for DELETE calls that should pass
    def test_delete_mtm_images_base_permission(self):
        user = self.create_user(self.base_permissions)
        user.groups.add(get_superadmins_group())
        organization = OrganizationFactory()
        kwargs = {"organization_code": organization.code}
        self.assert_delete_mtm_image(
            self.detail_view, self.field_name, organization.faq, denied=False, **kwargs
        )

    def test_delete_mtm_images_org_permission(self):
        _, _, organization = self.create_org_user(self.org_permissions)
        kwargs = {"organization_code": organization.code}
        self.assert_delete_mtm_image(
            self.detail_view, self.field_name, organization.faq, denied=False, **kwargs
        )

    # Tests for DELETE calls that should fail
    def test_delete_mtm_images_no_permission(self):
        self.create_user()
        organization = OrganizationFactory()
        kwargs = {"organization_code": organization.code}
        self.assert_delete_mtm_image(
            self.detail_view, self.field_name, organization.faq, denied=True, **kwargs
        )
