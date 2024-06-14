from django.urls import reverse
from parameterized import parameterized
from rest_framework import status

from apps.accounts.factories import PeopleGroupFactory, UserFactory
from apps.accounts.models import PeopleGroup, PrivacySettings, ProjectUser
from apps.commons.test import JwtAPITestCase, TestRoles
from apps.feedbacks.factories import CommentFactory, FollowFactory, ReviewFactory
from apps.invitations.factories import InvitationFactory
from apps.notifications.factories import NotificationFactory
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory
from apps.projects.models import Project


class UserPublicationStatusTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        cls.project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC,
            organizations=[cls.organization],
        )
        cls.people_group = PeopleGroupFactory(
            publication_status=PeopleGroup.PublicationStatus.PUBLIC,
            organization=cls.organization,
        )
        ProjectUser.objects.all().delete()  # Delete users created by the factories
        cls.users = {
            "public": UserFactory(
                publication_status=PrivacySettings.PrivacyChoices.PUBLIC,
                groups=[
                    cls.organization.get_users(),
                    cls.project.get_members(),
                    cls.people_group.get_members(),
                ],
            ),
            "private": UserFactory(
                publication_status=PrivacySettings.PrivacyChoices.HIDE,
                groups=[
                    cls.organization.get_users(),
                    cls.project.get_members(),
                    cls.people_group.get_members(),
                ],
            ),
            "org": UserFactory(
                publication_status=PrivacySettings.PrivacyChoices.ORGANIZATION,
                groups=[
                    cls.organization.get_users(),
                    cls.project.get_members(),
                    cls.people_group.get_members(),
                ],
            ),
        }
        cls.comments = {
            key: CommentFactory(author=value, project=cls.project)
            for key, value in cls.users.items()
        }
        cls.reviews = {
            key: ReviewFactory(reviewer=value, project=cls.project)
            for key, value in cls.users.items()
        }
        cls.follows = {
            key: FollowFactory(follower=value, project=cls.project)
            for key, value in cls.users.items()
        }
        cls.invitations = {
            key: InvitationFactory(owner=value, organization=cls.organization)
            for key, value in cls.users.items()
        }

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, ("public",)),
            (TestRoles.DEFAULT, ("public",)),
            (TestRoles.SUPERADMIN, ("public", "private", "org")),
            (TestRoles.ORG_ADMIN, ("public", "private", "org")),
            (TestRoles.ORG_FACILITATOR, ("public", "private", "org")),
            (TestRoles.ORG_USER, ("public", "org")),
        ]
    )
    def test_retrieve_users(self, role, expected_users):
        organization = self.organization
        user = self.get_parameterized_test_user(role, instances=[organization])
        self.client.force_authenticate(user)
        for user_type, user in self.users.items():
            response = self.client.get(reverse("ProjectUser-detail", args=(user.id,)))
            if user_type in expected_users:
                self.assertEqual(response.status_code, status.HTTP_200_OK)
            else:
                self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, ("public",)),
            (TestRoles.DEFAULT, ("public",)),
            (TestRoles.SUPERADMIN, ("public", "private", "org")),
            (TestRoles.ORG_ADMIN, ("public", "private", "org")),
            (TestRoles.ORG_FACILITATOR, ("public", "private", "org")),
            (TestRoles.ORG_USER, ("public", "org")),
        ]
    )
    def test_list_users(self, role, expected_users):
        organization = self.organization
        user = self.get_parameterized_test_user(role, instances=[organization])
        self.client.force_authenticate(user)
        response = self.client.get(reverse("ProjectUser-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        if user:
            self.assertEqual(len(content), len(expected_users) + 1)
            self.assertEqual(
                {user["id"] for user in content},
                {user.id, *[self.users[user_type].id for user_type in expected_users]},
            )
        else:
            self.assertEqual(len(content), len(expected_users))
            self.assertEqual(
                {user["id"] for user in content},
                {self.users[user_type].id for user_type in expected_users},
            )

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, ("public", None, None)),
            (TestRoles.DEFAULT, ("public", None, None)),
            (TestRoles.SUPERADMIN, ("public", "private", "org")),
            (TestRoles.ORG_ADMIN, ("public", "private", "org")),
            (TestRoles.ORG_FACILITATOR, ("public", "private", "org")),
            (TestRoles.ORG_USER, ("public", "org", None)),
        ]
    )
    def test_view_project_members(self, role, expected_users):
        organization = self.organization
        user = self.get_parameterized_test_user(role, instances=[organization])
        self.client.force_authenticate(user)
        response = self.client.get(reverse("Project-detail", args=(self.project.pk,)))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(len(content["team"]["members"]), len(expected_users))
        self.assertEqual(
            {user["id"] for user in content["team"]["members"]},
            {
                self.users[user_type].id if user_type in expected_users else None
                for user_type in self.users.keys()
            },
        )

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, ("public", None, None)),
            (TestRoles.DEFAULT, ("public", None, None)),
            (TestRoles.SUPERADMIN, ("public", "private", "org")),
            (TestRoles.ORG_ADMIN, ("public", "private", "org")),
            (TestRoles.ORG_FACILITATOR, ("public", "private", "org")),
            (TestRoles.ORG_USER, ("public", "org", None)),
        ]
    )
    def test_view_people_group_members(self, role, expected_users):
        organization = self.organization
        user = self.get_parameterized_test_user(role, instances=[organization])
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse(
                "PeopleGroup-member",
                args=(
                    organization.code,
                    self.people_group.pk,
                ),
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), len(expected_users))
        self.assertEqual(
            {user["id"] for user in content},
            {
                self.users[user_type].id if user_type in expected_users else None
                for user_type in self.users.keys()
            },
        )

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, ("public", None, None)),
            (TestRoles.DEFAULT, ("public", None, None)),
            (TestRoles.SUPERADMIN, ("public", "private", "org")),
            (TestRoles.ORG_ADMIN, ("public", "private", "org")),
            (TestRoles.ORG_FACILITATOR, ("public", "private", "org")),
            (TestRoles.ORG_USER, ("public", "org", None)),
        ]
    )
    def test_view_users_in_comments(self, role, expected_users):
        organization = self.organization
        user = self.get_parameterized_test_user(role, instances=[organization])
        self.client.force_authenticate(user)
        response = self.client.get(reverse("Comment-list", args=(self.project.id,)))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), len(expected_users))
        self.assertEqual(
            {(comment["author"]["id"], comment["id"]) for comment in content},
            {
                (
                    (self.users[user_type].id, self.comments[user_type].id)
                    if user_type in expected_users
                    else (None, self.comments[user_type].id)
                )
                for user_type in self.users.keys()
            },
        )

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, ("public", None, None)),
            (TestRoles.DEFAULT, ("public", None, None)),
            (TestRoles.SUPERADMIN, ("public", "private", "org")),
            (TestRoles.ORG_ADMIN, ("public", "private", "org")),
            (TestRoles.ORG_FACILITATOR, ("public", "private", "org")),
            (TestRoles.ORG_USER, ("public", "org", None)),
        ]
    )
    def test_view_users_in_follows(self, role, expected_users):
        organization = self.organization
        user = self.get_parameterized_test_user(role, instances=[organization])
        self.client.force_authenticate(user)
        response = self.client.get(reverse("Followed-list", args=(self.project.id,)))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), len(expected_users))
        self.assertEqual(
            {(follow["follower"]["id"], follow["id"]) for follow in content},
            {
                (
                    (self.users[user_type].id, self.follows[user_type].id)
                    if user_type in expected_users
                    else (None, self.follows[user_type].id)
                )
                for user_type in self.users.keys()
            },
        )

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, ("public", None, None)),
            (TestRoles.DEFAULT, ("public", None, None)),
            (TestRoles.SUPERADMIN, ("public", "private", "org")),
            (TestRoles.ORG_ADMIN, ("public", "private", "org")),
            (TestRoles.ORG_FACILITATOR, ("public", "private", "org")),
            (TestRoles.ORG_USER, ("public", "org", None)),
        ]
    )
    def test_view_users_in_reviews(self, role, expected_users):
        organization = self.organization
        user = self.get_parameterized_test_user(role, instances=[organization])
        self.client.force_authenticate(user)
        response = self.client.get(reverse("Reviewed-list", args=(self.project.id,)))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), len(expected_users))
        self.assertEqual(
            {(review["reviewer"]["id"], review["id"]) for review in content},
            {
                (
                    (self.users[user_type].id, self.reviews[user_type].id)
                    if user_type in expected_users
                    else (None, self.reviews[user_type].id)
                )
                for user_type in self.users.keys()
            },
        )

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, ("public", None, None)),
            (TestRoles.DEFAULT, ("public", None, None)),
            (TestRoles.SUPERADMIN, ("public", "private", "org")),
            (TestRoles.ORG_ADMIN, ("public", "private", "org")),
            (TestRoles.ORG_FACILITATOR, ("public", "private", "org")),
            (TestRoles.ORG_USER, ("public", "org", None)),
        ]
    )
    def test_view_users_in_invitations(self, role, expected_users):
        organization = self.organization
        user = self.get_parameterized_test_user(role, instances=[organization])
        self.client.force_authenticate(user)
        response = self.client.get(
            reverse("Invitation-list", args=(self.organization.code,))
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), len(expected_users))
        self.assertEqual(
            {(invitation["owner"]["id"], invitation["id"]) for invitation in content},
            {
                (
                    (self.users[user_type].id, self.invitations[user_type].id)
                    if user_type in expected_users
                    else (None, self.invitations[user_type].id)
                )
                for user_type in self.users.keys()
            },
        )

    @parameterized.expand(
        [
            (TestRoles.DEFAULT, ("public", None, None)),
            (TestRoles.SUPERADMIN, ("public", "private", "org")),
            (TestRoles.ORG_ADMIN, ("public", "private", "org")),
            (TestRoles.ORG_FACILITATOR, ("public", "private", "org")),
            (TestRoles.ORG_USER, ("public", "org", None)),
        ]
    )
    def test_view_users_in_notifications(self, role, expected_users):
        organization = self.organization
        user = self.get_parameterized_test_user(role, instances=[organization])
        self.client.force_authenticate(user)
        notifications = {
            user_type: NotificationFactory(
                receiver=user, sender=self.users[user_type], project=self.project
            )
            for user_type in self.users.keys()
        }
        response = self.client.get(reverse("Notification-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(len(content), len(expected_users))
        self.assertEqual(
            {
                (notification["sender"]["id"], notification["id"])
                for notification in content
            },
            {
                (
                    (self.users[user_type].id, notifications[user_type].id)
                    if user_type in expected_users
                    else (None, notifications[user_type].id)
                )
                for user_type in self.users.keys()
            },
        )

    @parameterized.expand(
        [
            (TestRoles.ANONYMOUS, status.HTTP_401_UNAUTHORIZED),
            (TestRoles.DEFAULT, status.HTTP_403_FORBIDDEN),
            (TestRoles.SUPERADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_ADMIN, status.HTTP_200_OK),
            (TestRoles.ORG_FACILITATOR, status.HTTP_403_FORBIDDEN),
            (TestRoles.ORG_USER, status.HTTP_403_FORBIDDEN),
        ]
    )
    def test_get_user_by_email(self, role, expected_code):
        organization = self.organization
        user = self.get_parameterized_test_user(role, instances=[organization])
        self.client.force_authenticate(user)
        for user in self.users.values():
            response = self.client.get(
                reverse("ProjectUser-get-by-email", args=(user.email,))
            )
            response_2 = self.client.get(
                reverse("ProjectUser-get-by-email", args=(user.personal_email,))
            )
            self.assertEqual(response.status_code, expected_code)
            self.assertEqual(response_2.status_code, expected_code)
            if expected_code == status.HTTP_200_OK:
                content = response.json()
                self.assertEqual(content["id"], user.id)
                content_2 = response_2.json()
                self.assertEqual(content_2["id"], user.id)
