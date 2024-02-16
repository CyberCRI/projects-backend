from django.urls import reverse
from parameterized import parameterized
from rest_framework import status

from apps.accounts.factories import UserFactory
from apps.commons.test import JwtAPITestCase, TestRoles
from apps.feedbacks.factories import FollowFactory
from apps.feedbacks.models import Follow
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory
from apps.projects.models import Project


class CreateFollowTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.public_project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[cls.organization],
        )
        cls.org_project = ProjectFactory(
            publication_status=Project.PublicationStatus.ORG,
            organizations=[cls.organization],
        )
        cls.private_project = ProjectFactory(
            publication_status=Project.PublicationStatus.PRIVATE,
            organizations=[cls.organization],
        )
        cls.projects = {
            "public": cls.public_project,
            "org": cls.org_project,
            "private": cls.private_project,
        }

    @parameterized.expand(
        [
            (TestRoles.DEFAULT, ("public",)),
            (TestRoles.SUPERADMIN, ("public", "org", "private")),
            (TestRoles.ORG_ADMIN, ("public", "org", "private")),
            (TestRoles.ORG_FACILITATOR, ("public", "org", "private")),
            (TestRoles.ORG_USER, ("public", "org")),
            (TestRoles.PROJECT_MEMBER, ("public", "org", "private")),
            (TestRoles.PROJECT_OWNER, ("public", "org", "private")),
            (TestRoles.PROJECT_REVIEWER, ("public", "org", "private")),
        ]
    )
    def test_create_followed(self, role, created_comments):
        user = self.get_parameterized_test_user(
            role, instances=list(self.projects.values())
        )
        self.client.force_authenticate(user)
        for publication_status, project in self.projects.items():
            payload = {
                "project_id": project.id,
            }
            response = self.client.post(
                reverse("Followed-list", args=(project.id,)), data=payload
            )
            if publication_status in created_comments:
                assert response.status_code == status.HTTP_201_CREATED
                assert response.json()["project"]["id"] == project.id
                assert response.json()["follower"]["id"] == user.id
            else:
                assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_followed_anonymous(self):
        for project in self.projects.values():
            payload = {
                "project_id": project.id,
            }
            response = self.client.post(
                reverse("Followed-list", args=(project.id,)), data=payload
            )
            assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @parameterized.expand(
        [
            (TestRoles.DEFAULT, ("public",)),
            (TestRoles.SUPERADMIN, ("public", "org", "private")),
            (TestRoles.ORG_ADMIN, ("public", "org", "private")),
            (TestRoles.ORG_FACILITATOR, ("public", "org", "private")),
            (TestRoles.ORG_USER, ("public", "org")),
            (TestRoles.PROJECT_MEMBER, ("public", "org", "private")),
            (TestRoles.PROJECT_OWNER, ("public", "org", "private")),
            (TestRoles.PROJECT_REVIEWER, ("public", "org", "private")),
        ]
    )
    def test_create_follower(self, role, created_comments):
        user = self.get_parameterized_test_user(
            role, instances=list(self.projects.values())
        )
        self.client.force_authenticate(user)
        for publication_status, project in self.projects.items():
            payload = {
                "project_id": project.id,
            }
            response = self.client.post(
                reverse("Follower-list", args=(user.id,)), data=payload
            )
            if publication_status in created_comments:
                assert response.status_code == status.HTTP_201_CREATED
                assert response.json()["project"]["id"] == project.id
                assert response.json()["follower"]["id"] == user.id
            else:
                assert response.status_code == status.HTTP_403_FORBIDDEN

    @parameterized.expand(
        [
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_201_CREATED),
            (TestRoles.ORG_ADMIN, status.HTTP_201_CREATED),
            (TestRoles.ORG_FACILITATOR, status.HTTP_201_CREATED),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_MEMBER, status.HTTP_201_CREATED),
            (TestRoles.PROJECT_OWNER, status.HTTP_201_CREATED),
            (TestRoles.PROJECT_REVIEWER, status.HTTP_201_CREATED),
        ]
    )
    def test_create_many_follow(self, role, expected_code):
        instances = list(self.projects.values())
        user = self.get_parameterized_test_user(role, instances=instances)
        payload = {"follows": [{"project_id": project.id} for project in instances]}
        self.client.force_authenticate(user)
        user_response = self.client.post(
            reverse("Follower-follow-many", args=(user.id,)),
            data=payload,
        )
        assert user_response.status_code == expected_code
        if expected_code == status.HTTP_201_CREATED:
            assert len(user_response.json()) == len(instances)
            assert all(
                p.id in [f["project"]["id"] for f in user_response.json()]
                for p in instances
            )
            assert all(user.id == f["follower"]["id"] for f in user_response.json())


class DestroyFollowTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[cls.organization],
        )

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.OWNER, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_ADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_FACILITATOR, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_MEMBER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_OWNER, status.HTTP_204_NO_CONTENT),
            (TestRoles.PROJECT_REVIEWER, status.HTTP_204_NO_CONTENT),
        ]
    )
    def test_destroy_followed(self, role, expected_code):
        follow = FollowFactory(project=self.project)
        user = self.get_parameterized_test_user(
            role, instances=[self.project], owned_instance=follow
        )
        self.client.force_authenticate(user)
        project_response = self.client.delete(
            reverse(
                "Followed-detail",
                args=(
                    self.project.id,
                    follow.id,
                ),
            )
        )
        assert project_response.status_code == expected_code
        if expected_code == status.HTTP_204_NO_CONTENT:
            assert Follow.objects.filter(id=follow.id).exists() is False

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.OWNER, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_ADMIN, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_FACILITATOR, status.HTTP_204_NO_CONTENT),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_MEMBER, status.HTTP_403_FORBIDDEN),
            (TestRoles.PROJECT_OWNER, status.HTTP_204_NO_CONTENT),
            (TestRoles.PROJECT_REVIEWER, status.HTTP_204_NO_CONTENT),
        ]
    )
    def test_destroy_follower(self, role, expected_code):
        follower = UserFactory()
        instance = FollowFactory(follower=follower, project=self.project)
        user = self.get_parameterized_test_user(
            role, instances=[self.project], owned_instance=instance
        )
        self.client.force_authenticate(user)
        project_response = self.client.delete(
            reverse(
                "Follower-detail",
                args=(
                    follower.id,
                    instance.id,
                ),
            )
        )
        assert project_response.status_code == expected_code


class ListFollowTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.public_project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[cls.organization],
        )
        cls.org_project = ProjectFactory(
            publication_status=Project.PublicationStatus.ORG,
            organizations=[cls.organization],
        )
        cls.private_project = ProjectFactory(
            publication_status=Project.PublicationStatus.PRIVATE,
            organizations=[cls.organization],
        )
        cls.projects = {
            "public": cls.public_project,
            "org": cls.org_project,
            "private": cls.private_project,
        }
        cls.follower = UserFactory()
        cls.follows = {
            "public": FollowFactory(project=cls.public_project, follower=cls.follower),
            "org": FollowFactory(project=cls.org_project, follower=cls.follower),
            "private": FollowFactory(
                project=cls.private_project, follower=cls.follower
            ),
        }

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, ("public",)),
            (TestRoles.DEFAULT, ("public",)),
            (TestRoles.SUPERADMIN, ("public", "org", "private")),
            (TestRoles.OWNER, ("public", "org", "private")),
            (TestRoles.ORG_ADMIN, ("public", "org", "private")),
            (TestRoles.ORG_FACILITATOR, ("public", "org", "private")),
            (TestRoles.ORG_USER, ("public", "org")),
            (TestRoles.PROJECT_MEMBER, ("public", "org", "private")),
            (TestRoles.PROJECT_OWNER, ("public", "org", "private")),
            (TestRoles.PROJECT_REVIEWER, ("public", "org", "private")),
        ]
    )
    def test_list_follower(self, role, retrieved_follows):
        user = self.get_parameterized_test_user(
            role, instances=list(self.projects.values()), owned_instance=self.follower
        )
        self.client.force_authenticate(user)
        user_response = self.client.get(
            reverse(
                "Follower-list",
                args=(self.follower.id,),
            ),
        )
        assert user_response.status_code == status.HTTP_200_OK
        content = user_response.json()["results"]
        assert len(content) == len(retrieved_follows)
        assert {f["id"] for f in content} == {
            self.follows[f].id for f in retrieved_follows
        }

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, ("public",)),
            (TestRoles.DEFAULT, ("public",)),
            (TestRoles.SUPERADMIN, ("public", "org", "private")),
            (TestRoles.OWNER, ("public", "org", "private")),
            (TestRoles.ORG_ADMIN, ("public", "org", "private")),
            (TestRoles.ORG_FACILITATOR, ("public", "org", "private")),
            (TestRoles.ORG_USER, ("public", "org")),
            (TestRoles.PROJECT_MEMBER, ("public", "org", "private")),
            (TestRoles.PROJECT_OWNER, ("public", "org", "private")),
            (TestRoles.PROJECT_REVIEWER, ("public", "org", "private")),
        ]
    )
    def test_list_followed(self, role, retrieved_follows):
        user = self.get_parameterized_test_user(
            role, instances=list(self.projects.values()), owned_instance=self.follower
        )
        self.client.force_authenticate(user)
        for project_status, project in self.projects.items():
            project_response = self.client.get(
                reverse("Followed-list", args=(project.id,)),
            )
            assert project_response.status_code == status.HTTP_200_OK
            content = project_response.json()["results"]
            if project_status in retrieved_follows:
                assert self.follower.id in [f["follower"]["id"] for f in content]
            else:
                assert len(content) == 0
