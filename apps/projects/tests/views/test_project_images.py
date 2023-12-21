from apps.commons.test import ImageStorageTestCaseMixin, JwtAPITestCase
from apps.projects.factories import ProjectFactory
from apps.projects.models import Project


class ProjectImagesTestCase(JwtAPITestCase, ImageStorageTestCaseMixin):
    list_view = "Project-images-list"
    detail_view = "Project-images-detail"
    field_name = "images"
    base_permissions = ["projects.change_project", "projects.view_project"]
    org_permissions = ["organizations.change_project", "organizations.view_project"]
    project_permissions = ["projects.change_project", "projects.view_project"]

    # Tests for GET calls that should pass
    def test_get_public_project_images(self):
        project = ProjectFactory()
        kwargs = {"project_id": project.id}
        self.assert_get_image(self.detail_view, self.field_name, project, **kwargs)

    def test_get_project_images_base_permission(self):
        self.create_user(self.base_permissions)
        project = ProjectFactory(publication_status=Project.PublicationStatus.ORG)
        kwargs = {"project_id": project.id}
        self.assert_get_image(self.detail_view, self.field_name, project, **kwargs)
        project = ProjectFactory(publication_status=Project.PublicationStatus.ORG)
        kwargs = {"project_id": project.id}
        self.assert_get_image(self.detail_view, self.field_name, project, **kwargs)

    def test_get_org_project_images_org_permission(self):
        project, user, _ = self.create_org_user(self.org_permissions)
        project.publication_status = Project.PublicationStatus.ORG
        project.save()
        kwargs = {"project_id": project.id}
        self.assert_get_image(self.detail_view, self.field_name, project, **kwargs)

    def test_get_private_project_images_project_permission(self):
        project, _ = self.create_project_member(self.project_permissions)
        project.publication_status = Project.PublicationStatus.PRIVATE
        project.save()
        kwargs = {"project_id": project.id}
        self.assert_get_image(self.detail_view, self.field_name, project, **kwargs)

    def test_get_private_project_images_org_permission(self):
        project, user, _ = self.create_org_user(self.org_permissions)
        project.publication_status = Project.PublicationStatus.PRIVATE
        project.save()
        kwargs = {"project_id": project.id}
        self.assert_get_image(self.detail_view, self.field_name, project, **kwargs)

    # Tests for POST calls that should pass
    def test_upload_images_base_permission(self):
        self.create_user(self.base_permissions)
        kwargs = {"project_id": ProjectFactory().id}
        self.assert_image_upload(self.list_view, **kwargs)

    def test_upload_images_org_permission(self):
        project, user, _ = self.create_org_user(self.org_permissions)
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
        self.assert_image_upload(self.list_view, denied=True, **kwargs)

    # Tests for DELETE calls that should pass
    def test_delete_mtm_images_base_permission(self):
        self.create_user(self.base_permissions)
        project = ProjectFactory()
        kwargs = {"project_id": project.id}
        self.assert_delete_mtm_image(
            self.detail_view, self.field_name, project, **kwargs
        )

    def test_delete_mtm_images_org_permission(self):
        project, user, _ = self.create_org_user(self.org_permissions)
        kwargs = {"project_id": project.id}
        self.assert_delete_mtm_image(
            self.detail_view, self.field_name, project, **kwargs
        )

    def test_delete_mtm_images_project_permission(self):
        project, _ = self.create_project_member(self.project_permissions)
        kwargs = {"project_id": project.id}
        self.assert_delete_mtm_image(
            self.detail_view, self.field_name, project, **kwargs
        )

    # Tests for DELETE calls that should fail
    def test_delete_mtm_images_no_permission(self):
        self.create_user()
        project = ProjectFactory()
        kwargs = {"project_id": project.id}
        self.assert_delete_mtm_image(
            self.detail_view, self.field_name, project, denied=True, **kwargs
        )

    def test_delete_mtm_images_project_member(self):
        project, _ = self.create_project_member([])
        kwargs = {"project_id": project.id}
        self.assert_delete_mtm_image(
            self.detail_view,
            self.field_name,
            project,
            denied=True,
            **kwargs,
        )
