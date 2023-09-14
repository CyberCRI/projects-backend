from apps.commons.test import ImageStorageTestCaseMixin, JwtAPITestCase
from apps.projects.factories import ProjectFactory


class ProjectHeaderTestCase(JwtAPITestCase, ImageStorageTestCaseMixin):
    list_view = "Project-header-list"
    detail_view = "Project-header-detail"
    field_name = "header_image"
    base_permissions = ["projects.change_project"]
    org_permissions = ["organizations.change_project"]
    project_permissions = ["projects.change_project"]

    # Tests for POST calls that should pass
    def test_upload_images_base_permission(self):
        self.create_user(self.base_permissions)
        kwargs = {"project_id": ProjectFactory().id}
        self.assert_image_upload(self.list_view, **kwargs)

    def test_upload_images_org_permission(self):
        project, _, _ = self.create_org_user(self.org_permissions)
        kwargs = {"project_id": project.id}
        self.assert_image_upload(self.list_view, **kwargs)

    def test_upload_images_project_permission(self):
        project, _ = self.create_project_member(self.project_permissions)
        kwargs = {"project_id": project.id}
        self.assert_image_upload(self.list_view, **kwargs)

    # Tests for POST calls that should fail
    def test_upload_oversized_image(self):
        self.create_user(self.base_permissions)
        kwargs = {"project_id": ProjectFactory().id}
        self.assert_image_too_large(self.list_view, **kwargs)

    def test_upload_images_no_permission(self):
        self.create_user()
        kwargs = {"project_id": ProjectFactory().id}
        self.assert_image_upload(self.list_view, **kwargs, denied=True)

    # Tests for DELETE calls that should pass
    def test_delete_fk_images_base_permission(self):
        self.create_user(self.base_permissions)
        project = ProjectFactory()
        kwargs = {"project_id": project.id}
        self.assert_delete_fk_image(
            self.detail_view, self.field_name, project, **kwargs
        )

    def test_delete_fk_images_org_permission(self):
        project, _, _ = self.create_org_user(self.org_permissions)
        kwargs = {"project_id": project.id}
        self.assert_delete_fk_image(
            self.detail_view, self.field_name, project, **kwargs
        )

    def test_delete_fk_images_project_permission(self):
        project, _ = self.create_project_member(self.project_permissions)
        kwargs = {"project_id": project.id}
        self.assert_delete_fk_image(
            self.detail_view, self.field_name, project, **kwargs
        )

    # Tests for DELETE calls that should fail
    def test_delete_fk_images_no_permission(self):
        self.create_user()
        project = ProjectFactory()
        kwargs = {"project_id": project.id}
        self.assert_delete_fk_image(
            self.detail_view, self.field_name, project, denied=True, **kwargs
        )
