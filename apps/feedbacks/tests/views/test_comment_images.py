from apps.commons.test import ImageStorageTestCaseMixin, JwtAPITestCase
from apps.feedbacks.factories import CommentFactory
from apps.projects.factories import ProjectFactory
from apps.projects.models import Project


class CommentImagesTestCase(JwtAPITestCase, ImageStorageTestCaseMixin):
    list_view = "Comment-images-list"
    detail_view = "Comment-images-detail"
    field_name = "images"

    # Tests for GET calls that should pass
    def test_get_public_project_images(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.PUBLIC)
        comment = CommentFactory(project=project)
        kwargs = {"project_id": project.id}
        self.assert_get_image(self.detail_view, self.field_name, comment, **kwargs)

    def test_get_project_images_base_permission(self):
        project = ProjectFactory(publication_status=Project.PublicationStatus.ORG)
        comment = CommentFactory(project=project)
        kwargs = {"project_id": project.id}
        self.assert_get_image(self.detail_view, self.field_name, comment, **kwargs)
        project = ProjectFactory(publication_status=Project.PublicationStatus.PRIVATE)
        comment = CommentFactory(project=project)
        kwargs = {"project_id": project.id}
        self.assert_get_image(self.detail_view, self.field_name, comment, **kwargs)

    def test_get_org_project_images_org_permission(self):
        project, _, _ = self.create_org_user(
            permissions=["organizations.view_org_project"]
        )
        project.publication_status = Project.PublicationStatus.ORG
        project.save()
        comment = CommentFactory(project=project)
        kwargs = {"project_id": project.id}
        self.assert_get_image(self.detail_view, self.field_name, comment, **kwargs)

    def test_get_org_project_images_project_permission(self):
        project, _ = self.create_project_member(permissions=["project.view_project"])
        project.publication_status = Project.PublicationStatus.ORG
        project.save()
        comment = CommentFactory(project=project)
        kwargs = {"project_id": project.id}
        self.assert_get_image(self.detail_view, self.field_name, comment, **kwargs)

    def test_get_private_project_images_project_permissions(self):
        project, _ = self.create_project_member(permissions=["project.view_project"])
        project.publication_status = Project.PublicationStatus.PRIVATE
        project.save()
        comment = CommentFactory(project=project)
        kwargs = {"project_id": project.id}
        self.assert_get_image(self.detail_view, self.field_name, comment, **kwargs)

    def test_get_private_project_images_org_permission(self):
        project, _, _ = self.create_org_user(permissions=["organizations.view_project"])
        project.publication_status = Project.PublicationStatus.PRIVATE
        project.save()
        comment = CommentFactory(project=project)
        kwargs = {"project_id": project.id}
        self.assert_get_image(self.detail_view, self.field_name, comment, **kwargs)

    # Tests for POST calls that should pass
    def test_upload_images_base_permission(self):
        self.create_user()
        kwargs = {"project_id": ProjectFactory().id}
        self.assert_image_upload(self.list_view, **kwargs)

    def test_upload_images_org_permission(self):
        project, _, _ = self.create_org_user(
            permissions=["organizations.view_org_project"]
        )
        project.publication_status = Project.PublicationStatus.ORG
        project.save()
        kwargs = {"project_id": project.id}
        self.assert_image_upload(self.list_view, **kwargs)

    def test_upload_images_project_permission(self):
        project, _ = self.create_project_member(permissions=["project.view_project"])
        project.publication_status = Project.PublicationStatus.PRIVATE
        project.save()
        kwargs = {"project_id": project.id}
        self.assert_image_upload(self.list_view, **kwargs)

    # Tests for POST calls that should fail
    def test_upload_oversized_image(self):
        self.create_user()
        project = ProjectFactory()
        kwargs = {"project_id": project.id}
        self.assert_image_too_large(self.list_view, **kwargs)

    # Tests for DELETE calls that should pass
    def test_delete_mtm_images_base_permission(self):
        self.create_user(["feedbacks.delete_comment"])
        project = ProjectFactory()
        kwargs = {"project_id": project.id}
        self.assert_delete_mtm_image(
            self.detail_view, self.field_name, CommentFactory(project=project), **kwargs
        )

    def test_delete_mtm_images_org_permission(self):
        project, user, _ = self.create_org_user(["organizations.delete_comment"])
        user.refresh_from_db()
        kwargs = {"project_id": project.id}
        self.assert_delete_mtm_image(
            self.detail_view,
            self.field_name,
            CommentFactory(project=project),
            **kwargs,
        )

    def test_delete_mtm_images_project_permission(self):
        project, _ = self.create_project_member(["projects.delete_comment"])
        kwargs = {"project_id": project.id}
        self.assert_delete_mtm_image(
            self.detail_view,
            self.field_name,
            CommentFactory(project=project),
            **kwargs,
        )

    # Tests for DELETE calls that should fail
    def test_delete_mtm_images_no_permission(self):
        self.create_user()
        project = ProjectFactory()
        kwargs = {"project_id": project.id}
        self.assert_delete_mtm_image(
            self.detail_view,
            self.field_name,
            CommentFactory(project=project),
            denied=True,
            **kwargs,
        )
