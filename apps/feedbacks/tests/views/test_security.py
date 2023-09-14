from django.urls import reverse

from apps.accounts.factories import UserFactory
from apps.commons.test import JwtAPITestCase
from apps.projects.factories import ProjectFactory
from apps.projects.models import Project


class FeedbacksSecurityTestCase(JwtAPITestCase):
    def test_create_impersonate(self):
        """Test that we can't impersonate user"""
        project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            life_status=Project.LifeStatus.TO_REVIEW,
        )
        user = UserFactory(
            permissions=[
                ("feedbacks.add_review", None),
                ("feedbacks.add_follow", None),
                ("feedbacks.add_comment", None),
            ]
        )
        other_user = UserFactory()
        payload = {
            "project_id": project.id,
            "reviewer_id": other_user.id,
            "follower_id": other_user.id,
            "author_id": other_user.id,
            "title": "Title",
            "description": "Description",
        }
        self.client.force_authenticate(user)
        response = self.client.post(
            reverse("Reviewed-list", kwargs={"project_id": project.id}), data=payload
        )
        assert response.data["reviewer"]["id"] == user.id

        response = self.client.post(
            reverse("Followed-list", kwargs={"project_id": project.id}), data=payload
        )
        assert response.data["follower"]["id"] == user.id

        response = self.client.post(
            reverse("Comment-list", kwargs={"project_id": project.id}), data=payload
        )
        assert response.data["author"]["id"] == user.id
