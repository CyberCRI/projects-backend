from apps.commons.test import ImageStorageTestCaseMixin, JwtAPITestCase
from apps.organizations.factories import OrganizationFactory


class OrganizationBannerTestCase(JwtAPITestCase, ImageStorageTestCaseMixin):
    list_view = "Organization-banner-list"
    detail_view = "Organization-banner-detail"
    field_name = "banner_image"
    base_permissions = ["organizations.change_organization"]
    org_permissions = ["organizations.change_organization"]

    # Tests for POST calls that should pass
    def test_upload_images_base_permission(self):
        self.create_user(self.base_permissions)
        organization = OrganizationFactory()
        kwargs = {"organization_code": organization.code}
        self.assert_image_upload(self.list_view, **kwargs)

    def test_upload_images_org_permission(self):
        _, _, organization = self.create_org_user(self.org_permissions)
        kwargs = {"organization_code": organization.code}
        self.assert_image_upload(self.list_view, **kwargs)

    # Tests for POST calls that should fail
    def test_upload_oversized_image(self):
        self.create_user(self.base_permissions)
        organization = OrganizationFactory()
        kwargs = {"organization_code": organization.code}
        self.assert_image_too_large(self.list_view, **kwargs)

    def test_upload_images_no_permission(self):
        self.create_user()
        organization = OrganizationFactory()
        kwargs = {"organization_code": organization.code}
        self.assert_image_upload(self.list_view, denied=True, **kwargs)
