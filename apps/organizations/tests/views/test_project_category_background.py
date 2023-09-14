from apps.accounts.utils import get_superadmins_group
from apps.commons.test import ImageStorageTestCaseMixin, JwtAPITestCase
from apps.organizations.factories import OrganizationFactory, ProjectCategoryFactory


class ProjectCategoryBackgroundTestCase(JwtAPITestCase, ImageStorageTestCaseMixin):
    list_view = "Category-background-list"
    detail_view = "Category-background-detail"
    field_name = "background_image"
    base_permissions = []
    org_permissions = ["organizations.change_projectcategory"]

    @staticmethod
    def create_project_category(organization):
        project_category = ProjectCategoryFactory()
        project_category.organization = organization
        project_category.save()
        return project_category

    # Tests for POST calls that should pass
    def test_upload_images_base_permission(self):
        user = self.create_user(self.base_permissions)
        user.groups.add(get_superadmins_group())
        project_category = ProjectCategoryFactory()
        kwargs = {"category_id": project_category.id}
        self.assert_image_upload(self.list_view, **kwargs)

    # Tests for POST calls that should fail
    def test_upload_oversized_image(self):
        user = self.create_user(self.base_permissions)
        user.groups.add(get_superadmins_group())
        project_category = ProjectCategoryFactory()
        kwargs = {"category_id": project_category.id}
        self.assert_image_too_large(self.list_view, **kwargs)

    def test_upload_images_org_permission(self):
        _, _, organization = self.create_org_user(self.org_permissions)
        project_category = self.create_project_category(organization)
        kwargs = {"category_id": project_category.id}
        self.assert_image_upload(self.list_view, **kwargs)

    def test_upload_images_no_permission(self):
        self.create_user()
        project_category = ProjectCategoryFactory()
        kwargs = {"category_id": project_category.id}
        self.assert_image_upload(self.list_view, denied=True, **kwargs)

    # Tests for DELETE calls that should pass
    def test_delete_fk_images_base_permission(self):
        user = self.create_user(self.base_permissions)
        user.groups.add(get_superadmins_group())
        project_category = ProjectCategoryFactory()
        kwargs = {"category_id": project_category.id}
        self.assert_delete_fk_image(
            self.detail_view, self.field_name, project_category, denied=False, **kwargs
        )

    def test_delete_fk_images_org_permission(self):
        _, _, organization = self.create_org_user(self.org_permissions)
        project_category = self.create_project_category(organization)
        kwargs = {"category_id": project_category.id}
        self.assert_delete_fk_image(
            self.detail_view, self.field_name, project_category, denied=False, **kwargs
        )

    # Tests for DELETE calls that should fail
    def test_delete_fk_images_user(self):
        organization = OrganizationFactory()
        project_category = self.create_project_category(organization)
        self.create_user()
        kwargs = {"category_id": project_category.id}
        self.assert_delete_fk_image(
            self.detail_view, self.field_name, project_category, denied=True, **kwargs
        )
