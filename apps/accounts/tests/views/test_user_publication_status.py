from django.urls import reverse

from apps.accounts.factories import PeopleGroupFactory, SeedUserFactory, UserFactory
from apps.accounts.models import PeopleGroup, PrivacySettings, ProjectUser
from apps.accounts.utils import get_superadmins_group
from apps.commons.test import JwtAPITestCase
from apps.feedbacks.factories import CommentFactory, FollowFactory, ReviewFactory
from apps.invitations.factories import InvitationFactory
from apps.notifications.factories import NotificationFactory
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory
from apps.projects.models import Project


class UserPublicationStatusTestCase(JwtAPITestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.organization = OrganizationFactory()
        cls.project = ProjectFactory(
            publication_status=Project.PublicationStatus.PUBLIC
        )
        cls.people_group = PeopleGroupFactory(
            publication_status=PeopleGroup.PublicationStatus.PUBLIC
        )
        ProjectUser.objects.all().delete()  # Delete users created by the factories
        cls.public_user = UserFactory(
            publication_status=PrivacySettings.PrivacyChoices.PUBLIC
        )
        cls.private_user = UserFactory(
            publication_status=PrivacySettings.PrivacyChoices.HIDE
        )
        cls.org_user = UserFactory(
            publication_status=PrivacySettings.PrivacyChoices.ORGANIZATION
        )
        cls.organization.users.add(cls.org_user, cls.public_user, cls.private_user)
        cls.project.members.add(cls.public_user, cls.private_user, cls.org_user)
        cls.people_group.members.add(cls.public_user, cls.private_user, cls.org_user)


class AnonymousUserTestCase(UserPublicationStatusTestCase):
    def test_retrieve_user_with_keycloak_import(self):
        user = SeedUserFactory(publication_status=PrivacySettings.PrivacyChoices.HIDE)
        response = self.client.get(
            reverse("ProjectUser-detail", args=(user.keycloak_id,))
        )
        self.assertEqual(response.status_code, 404)
        user.delete()

    def test_retrieve_users(self):
        for user in [self.public_user, self.private_user, self.org_user]:
            response = self.client.get(
                reverse("ProjectUser-detail", args=(user.keycloak_id,))
            )
            if user == self.public_user:
                self.assertEqual(response.status_code, 200)
            else:
                self.assertEqual(response.status_code, 404)

    def test_list_users(self):
        response = self.client.get(reverse("ProjectUser-list"))
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 1)
        self.assertEqual({user["id"] for user in content}, {self.public_user.id})

    def test_view_project_members(self):
        response = self.client.get(reverse("Project-detail", args=(self.project.pk,)))
        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(len(content["team"]["members"]), 3)
        self.assertEqual(
            {user["id"] for user in content["team"]["members"]},
            {self.public_user.id, None, None},
        )

    def test_view_people_group_members(self):
        response = self.client.get(
            reverse(
                "PeopleGroup-member",
                args=(
                    self.people_group.organization.code,
                    self.people_group.pk,
                ),
            )
        )
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 3)
        self.assertEqual(
            {user["id"] for user in content}, {self.public_user.id, None, None}
        )

    def test_view_users_in_comments(self):
        public_comment = CommentFactory(author=self.public_user, project=self.project)
        private_comment = CommentFactory(author=self.private_user, project=self.project)
        org_comment = CommentFactory(author=self.org_user, project=self.project)
        response = self.client.get(reverse("Comment-list", args=[self.project.id]))
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 3)
        self.assertEqual(
            {(comment["author"]["id"], comment["id"]) for comment in content},
            {
                (self.public_user.id, public_comment.id),
                (None, private_comment.id),
                (None, org_comment.id),
            },
        )

    def test_view_users_in_follows(self):
        public_follow = FollowFactory(follower=self.public_user, project=self.project)
        private_follow = FollowFactory(follower=self.private_user, project=self.project)
        org_follow = FollowFactory(follower=self.org_user, project=self.project)
        response = self.client.get(reverse("Followed-list", args=(self.project.id,)))
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 3)
        self.assertEqual(
            {(follow["follower"]["id"], follow["id"]) for follow in content},
            {
                (self.public_user.id, public_follow.id),
                (None, private_follow.id),
                (None, org_follow.id),
            },
        )

    def test_view_users_in_reviews(self):
        public_review = ReviewFactory(reviewer=self.public_user, project=self.project)
        private_review = ReviewFactory(reviewer=self.private_user, project=self.project)
        org_review = ReviewFactory(reviewer=self.org_user, project=self.project)
        response = self.client.get(reverse("Reviewed-list", args=(self.project.id,)))
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 3)
        self.assertEqual(
            {(review["reviewer"]["id"], review["id"]) for review in content},
            {
                (self.public_user.id, public_review.id),
                (None, private_review.id),
                (None, org_review.id),
            },
        )

    def test_view_users_in_invitations(self):
        public_invitation = InvitationFactory(
            owner=self.public_user, organization=self.organization
        )
        private_invitation = InvitationFactory(
            owner=self.private_user, organization=self.organization
        )
        org_invitation = InvitationFactory(
            owner=self.org_user, organization=self.organization
        )
        response = self.client.get(
            reverse("Invitation-list", args=(self.organization.code,))
        )
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 3)
        self.assertEqual(
            {(invitation["owner"]["id"], invitation["id"]) for invitation in content},
            {
                (self.public_user.id, public_invitation.id),
                (None, private_invitation.id),
                (None, org_invitation.id),
            },
        )


class AuthenticatedUserTestCase(UserPublicationStatusTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = UserFactory(publication_status=PrivacySettings.PrivacyChoices.HIDE)

    def setUp(self):
        self.client.force_authenticate(self.user)

    def test_retrieve_users(self):
        for user in [self.public_user, self.private_user, self.org_user, self.user]:
            response = self.client.get(
                reverse("ProjectUser-detail", args=(user.keycloak_id,))
            )
            if user == self.public_user or user == self.user:
                self.assertEqual(response.status_code, 200)
            else:
                self.assertEqual(response.status_code, 404)

    def test_list_users(self):
        response = self.client.get(reverse("ProjectUser-list"))
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 2)
        self.assertEqual(
            {user["id"] for user in content}, {self.public_user.id, self.user.id}
        )

    def test_view_project_members(self):
        response = self.client.get(reverse("Project-detail", args=(self.project.pk,)))
        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(len(content["team"]["members"]), 3)
        self.assertEqual(
            {user["id"] for user in content["team"]["members"]},
            {self.public_user.id, None, None},
        )

    def test_view_people_group_members(self):
        response = self.client.get(
            reverse(
                "PeopleGroup-member",
                args=(
                    self.people_group.organization.code,
                    self.people_group.pk,
                ),
            )
        )
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 3)
        self.assertEqual(
            {user["id"] for user in content}, {self.public_user.id, None, None}
        )

    def test_view_users_in_comments(self):
        public_comment = CommentFactory(author=self.public_user, project=self.project)
        private_comment = CommentFactory(author=self.private_user, project=self.project)
        org_comment = CommentFactory(author=self.org_user, project=self.project)
        response = self.client.get(reverse("Comment-list", args=[self.project.id]))
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 3)
        self.assertEqual(
            {(comment["author"]["id"], comment["id"]) for comment in content},
            {
                (self.public_user.id, public_comment.id),
                (None, private_comment.id),
                (None, org_comment.id),
            },
        )

    def test_view_users_in_follows(self):
        public_follow = FollowFactory(follower=self.public_user, project=self.project)
        private_follow = FollowFactory(follower=self.private_user, project=self.project)
        org_follow = FollowFactory(follower=self.org_user, project=self.project)
        response = self.client.get(reverse("Followed-list", args=(self.project.id,)))
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 3)
        self.assertEqual(
            {(follow["follower"]["id"], follow["id"]) for follow in content},
            {
                (self.public_user.id, public_follow.id),
                (None, private_follow.id),
                (None, org_follow.id),
            },
        )

    def test_view_users_in_reviews(self):
        public_review = ReviewFactory(reviewer=self.public_user, project=self.project)
        private_review = ReviewFactory(reviewer=self.private_user, project=self.project)
        org_review = ReviewFactory(reviewer=self.org_user, project=self.project)
        response = self.client.get(reverse("Reviewed-list", args=(self.project.id,)))
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 3)
        self.assertEqual(
            {(review["reviewer"]["id"], review["id"]) for review in content},
            {
                (self.public_user.id, public_review.id),
                (None, private_review.id),
                (None, org_review.id),
            },
        )

    def test_view_users_in_invitations(self):
        public_invitation = InvitationFactory(
            owner=self.public_user, organization=self.organization
        )
        private_invitation = InvitationFactory(
            owner=self.private_user, organization=self.organization
        )
        org_invitation = InvitationFactory(
            owner=self.org_user, organization=self.organization
        )
        response = self.client.get(
            reverse("Invitation-list", args=(self.organization.code,))
        )
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 3)
        self.assertEqual(
            {(invitation["owner"]["id"], invitation["id"]) for invitation in content},
            {
                (self.public_user.id, public_invitation.id),
                (None, private_invitation.id),
                (None, org_invitation.id),
            },
        )

    def test_view_users_in_notifications(self):
        public_notification = NotificationFactory(
            receiver=self.user, sender=self.public_user
        )
        private_notification = NotificationFactory(
            receiver=self.user, sender=self.private_user
        )
        org_notification = NotificationFactory(receiver=self.user, sender=self.org_user)
        response = self.client.get(reverse("Notification-list"))
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 3)
        self.assertEqual(
            {
                (notification["sender"]["id"], notification["id"])
                for notification in content
            },
            {
                (self.public_user.id, public_notification.id),
                (None, private_notification.id),
                (None, org_notification.id),
            },
        )


class OrganizationMemberTestCase(UserPublicationStatusTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = UserFactory(publication_status=PrivacySettings.PrivacyChoices.HIDE)
        cls.organization.users.add(cls.user)

    def setUp(self):
        self.client.force_authenticate(self.user)

    def test_retrieve_users(self):
        for user in [self.public_user, self.private_user, self.org_user, self.user]:
            response = self.client.get(
                reverse("ProjectUser-detail", args=(user.keycloak_id,))
            )
            if user != self.private_user:
                self.assertEqual(response.status_code, 200)
            else:
                self.assertEqual(response.status_code, 404)

    def test_list_users(self):
        response = self.client.get(reverse("ProjectUser-list"))
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 3)
        self.assertEqual(
            {user["id"] for user in content},
            {self.public_user.id, self.user.id, self.org_user.id},
        )

    def test_view_project_members(self):
        response = self.client.get(reverse("Project-detail", args=(self.project.pk,)))
        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(len(content["team"]["members"]), 3)
        self.assertEqual(
            {user["id"] for user in content["team"]["members"]},
            {self.public_user.id, self.org_user.id, None},
        )

    def test_view_people_group_members(self):
        response = self.client.get(
            reverse(
                "PeopleGroup-member",
                args=(
                    self.people_group.organization.code,
                    self.people_group.pk,
                ),
            )
        )
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 3)
        self.assertEqual(
            {user["id"] for user in content},
            {self.public_user.id, self.org_user.id, None},
        )

    def test_view_users_in_comments(self):
        public_comment = CommentFactory(author=self.public_user, project=self.project)
        private_comment = CommentFactory(author=self.private_user, project=self.project)
        org_comment = CommentFactory(author=self.org_user, project=self.project)
        response = self.client.get(reverse("Comment-list", args=[self.project.id]))
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 3)
        self.assertEqual(
            {(comment["author"]["id"], comment["id"]) for comment in content},
            {
                (self.public_user.id, public_comment.id),
                (None, private_comment.id),
                (self.org_user.id, org_comment.id),
            },
        )

    def test_view_users_in_follows(self):
        public_follow = FollowFactory(follower=self.public_user, project=self.project)
        private_follow = FollowFactory(follower=self.private_user, project=self.project)
        org_follow = FollowFactory(follower=self.org_user, project=self.project)
        response = self.client.get(reverse("Followed-list", args=(self.project.id,)))
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 3)
        self.assertEqual(
            {(follow["follower"]["id"], follow["id"]) for follow in content},
            {
                (self.public_user.id, public_follow.id),
                (None, private_follow.id),
                (self.org_user.id, org_follow.id),
            },
        )

    def test_view_users_in_reviews(self):
        public_review = ReviewFactory(reviewer=self.public_user, project=self.project)
        private_review = ReviewFactory(reviewer=self.private_user, project=self.project)
        org_review = ReviewFactory(reviewer=self.org_user, project=self.project)
        response = self.client.get(reverse("Reviewed-list", args=(self.project.id,)))
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 3)
        self.assertEqual(
            {(review["reviewer"]["id"], review["id"]) for review in content},
            {
                (self.public_user.id, public_review.id),
                (None, private_review.id),
                (self.org_user.id, org_review.id),
            },
        )

    def test_view_users_in_invitations(self):
        public_invitation = InvitationFactory(
            owner=self.public_user, organization=self.organization
        )
        private_invitation = InvitationFactory(
            owner=self.private_user, organization=self.organization
        )
        org_invitation = InvitationFactory(
            owner=self.org_user, organization=self.organization
        )
        response = self.client.get(
            reverse("Invitation-list", args=(self.organization.code,))
        )
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 3)
        self.assertEqual(
            {(invitation["owner"]["id"], invitation["id"]) for invitation in content},
            {
                (self.public_user.id, public_invitation.id),
                (None, private_invitation.id),
                (self.org_user.id, org_invitation.id),
            },
        )

    def test_view_users_in_notifications(self):
        public_notification = NotificationFactory(
            receiver=self.user, sender=self.public_user
        )
        private_notification = NotificationFactory(
            receiver=self.user, sender=self.private_user
        )
        org_notification = NotificationFactory(receiver=self.user, sender=self.org_user)
        response = self.client.get(reverse("Notification-list"))
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 3)
        self.assertEqual(
            {
                (notification["sender"]["id"], notification["id"])
                for notification in content
            },
            {
                (self.public_user.id, public_notification.id),
                (None, private_notification.id),
                (self.org_user.id, org_notification.id),
            },
        )


class OrganizationFacilitatorTestCase(UserPublicationStatusTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = UserFactory(publication_status=PrivacySettings.PrivacyChoices.HIDE)
        cls.organization.facilitators.add(cls.user)

    def setUp(self):
        self.client.force_authenticate(self.user)

    def test_retrieve_users(self):
        for user in [self.public_user, self.private_user, self.org_user, self.user]:
            response = self.client.get(
                reverse("ProjectUser-detail", args=(user.keycloak_id,))
            )
            self.assertEqual(response.status_code, 200)

    def test_list_users(self):
        response = self.client.get(reverse("ProjectUser-list"))
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 4)
        self.assertEqual(
            {user["id"] for user in content},
            {self.public_user.id, self.user.id, self.org_user.id, self.private_user.id},
        )

    def test_view_project_members(self):
        response = self.client.get(reverse("Project-detail", args=(self.project.pk,)))
        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(len(content["team"]["members"]), 3)
        self.assertEqual(
            {user["id"] for user in content["team"]["members"]},
            {self.public_user.id, self.org_user.id, self.private_user.id},
        )

    def test_view_people_group_members(self):
        response = self.client.get(
            reverse(
                "PeopleGroup-member",
                args=(
                    self.people_group.organization.code,
                    self.people_group.pk,
                ),
            )
        )
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 3)
        self.assertEqual(
            {user["id"] for user in content},
            {self.public_user.id, self.org_user.id, self.private_user.id},
        )

    def test_view_users_in_comments(self):
        public_comment = CommentFactory(author=self.public_user, project=self.project)
        private_comment = CommentFactory(author=self.private_user, project=self.project)
        org_comment = CommentFactory(author=self.org_user, project=self.project)
        response = self.client.get(reverse("Comment-list", args=[self.project.id]))
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 3)
        self.assertEqual(
            {(comment["author"]["id"], comment["id"]) for comment in content},
            {
                (self.public_user.id, public_comment.id),
                (self.private_user.id, private_comment.id),
                (self.org_user.id, org_comment.id),
            },
        )

    def test_view_users_in_follows(self):
        public_follow = FollowFactory(follower=self.public_user, project=self.project)
        private_follow = FollowFactory(follower=self.private_user, project=self.project)
        org_follow = FollowFactory(follower=self.org_user, project=self.project)
        response = self.client.get(reverse("Followed-list", args=(self.project.id,)))
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 3)
        self.assertEqual(
            {(follow["follower"]["id"], follow["id"]) for follow in content},
            {
                (self.public_user.id, public_follow.id),
                (self.private_user.id, private_follow.id),
                (self.org_user.id, org_follow.id),
            },
        )

    def test_view_users_in_reviews(self):
        public_review = ReviewFactory(reviewer=self.public_user, project=self.project)
        private_review = ReviewFactory(reviewer=self.private_user, project=self.project)
        org_review = ReviewFactory(reviewer=self.org_user, project=self.project)
        response = self.client.get(reverse("Reviewed-list", args=(self.project.id,)))
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 3)
        self.assertEqual(
            {(review["reviewer"]["id"], review["id"]) for review in content},
            {
                (self.public_user.id, public_review.id),
                (self.private_user.id, private_review.id),
                (self.org_user.id, org_review.id),
            },
        )

    def test_view_users_in_invitations(self):
        public_invitation = InvitationFactory(
            owner=self.public_user, organization=self.organization
        )
        private_invitation = InvitationFactory(
            owner=self.private_user, organization=self.organization
        )
        org_invitation = InvitationFactory(
            owner=self.org_user, organization=self.organization
        )
        response = self.client.get(
            reverse("Invitation-list", args=(self.organization.code,))
        )
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 3)
        self.assertEqual(
            {(invitation["owner"]["id"], invitation["id"]) for invitation in content},
            {
                (self.public_user.id, public_invitation.id),
                (self.private_user.id, private_invitation.id),
                (self.org_user.id, org_invitation.id),
            },
        )

    def test_view_users_in_notifications(self):
        public_notification = NotificationFactory(
            receiver=self.user, sender=self.public_user
        )
        private_notification = NotificationFactory(
            receiver=self.user, sender=self.private_user
        )
        org_notification = NotificationFactory(receiver=self.user, sender=self.org_user)
        response = self.client.get(reverse("Notification-list"))
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 3)
        self.assertEqual(
            {
                (notification["sender"]["id"], notification["id"])
                for notification in content
            },
            {
                (self.public_user.id, public_notification.id),
                (self.private_user.id, private_notification.id),
                (self.org_user.id, org_notification.id),
            },
        )


class OrganizationAdminTestCase(UserPublicationStatusTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = UserFactory(publication_status=PrivacySettings.PrivacyChoices.HIDE)
        cls.organization.admins.add(cls.user)

    def setUp(self):
        self.client.force_authenticate(self.user)

    def test_retrieve_users(self):
        for user in [self.public_user, self.private_user, self.org_user, self.user]:
            response = self.client.get(
                reverse("ProjectUser-detail", args=(user.keycloak_id,))
            )
            self.assertEqual(response.status_code, 200)

    def test_list_users(self):
        response = self.client.get(reverse("ProjectUser-list"))
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 4)
        self.assertEqual(
            {user["id"] for user in content},
            {self.public_user.id, self.user.id, self.org_user.id, self.private_user.id},
        )

    def test_view_project_members(self):
        response = self.client.get(reverse("Project-detail", args=(self.project.pk,)))
        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(len(content["team"]["members"]), 3)
        self.assertEqual(
            {user["id"] for user in content["team"]["members"]},
            {self.public_user.id, self.org_user.id, self.private_user.id},
        )

    def test_view_people_group_members(self):
        response = self.client.get(
            reverse(
                "PeopleGroup-member",
                args=(
                    self.people_group.organization.code,
                    self.people_group.pk,
                ),
            )
        )
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 3)
        self.assertEqual(
            {user["id"] for user in content},
            {self.public_user.id, self.org_user.id, self.private_user.id},
        )

    def test_view_users_in_comments(self):
        public_comment = CommentFactory(author=self.public_user, project=self.project)
        private_comment = CommentFactory(author=self.private_user, project=self.project)
        org_comment = CommentFactory(author=self.org_user, project=self.project)
        response = self.client.get(reverse("Comment-list", args=[self.project.id]))
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 3)
        self.assertEqual(
            {(comment["author"]["id"], comment["id"]) for comment in content},
            {
                (self.public_user.id, public_comment.id),
                (self.private_user.id, private_comment.id),
                (self.org_user.id, org_comment.id),
            },
        )

    def test_view_users_in_follows(self):
        public_follow = FollowFactory(follower=self.public_user, project=self.project)
        private_follow = FollowFactory(follower=self.private_user, project=self.project)
        org_follow = FollowFactory(follower=self.org_user, project=self.project)
        response = self.client.get(reverse("Followed-list", args=(self.project.id,)))
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 3)
        self.assertEqual(
            {(follow["follower"]["id"], follow["id"]) for follow in content},
            {
                (self.public_user.id, public_follow.id),
                (self.private_user.id, private_follow.id),
                (self.org_user.id, org_follow.id),
            },
        )

    def test_view_users_in_reviews(self):
        public_review = ReviewFactory(reviewer=self.public_user, project=self.project)
        private_review = ReviewFactory(reviewer=self.private_user, project=self.project)
        org_review = ReviewFactory(reviewer=self.org_user, project=self.project)
        response = self.client.get(reverse("Reviewed-list", args=(self.project.id,)))
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 3)
        self.assertEqual(
            {(review["reviewer"]["id"], review["id"]) for review in content},
            {
                (self.public_user.id, public_review.id),
                (self.private_user.id, private_review.id),
                (self.org_user.id, org_review.id),
            },
        )

    def test_view_users_in_invitations(self):
        public_invitation = InvitationFactory(
            owner=self.public_user, organization=self.organization
        )
        private_invitation = InvitationFactory(
            owner=self.private_user, organization=self.organization
        )
        org_invitation = InvitationFactory(
            owner=self.org_user, organization=self.organization
        )
        response = self.client.get(
            reverse("Invitation-list", args=(self.organization.code,))
        )
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 3)
        self.assertEqual(
            {(invitation["owner"]["id"], invitation["id"]) for invitation in content},
            {
                (self.public_user.id, public_invitation.id),
                (self.private_user.id, private_invitation.id),
                (self.org_user.id, org_invitation.id),
            },
        )

    def test_view_users_in_notifications(self):
        public_notification = NotificationFactory(
            receiver=self.user, sender=self.public_user
        )
        private_notification = NotificationFactory(
            receiver=self.user, sender=self.private_user
        )
        org_notification = NotificationFactory(receiver=self.user, sender=self.org_user)
        response = self.client.get(reverse("Notification-list"))
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 3)
        self.assertEqual(
            {
                (notification["sender"]["id"], notification["id"])
                for notification in content
            },
            {
                (self.public_user.id, public_notification.id),
                (self.private_user.id, private_notification.id),
                (self.org_user.id, org_notification.id),
            },
        )


class SuperAdminTestCase(UserPublicationStatusTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = UserFactory(
            groups=[get_superadmins_group()],
            publication_status=PrivacySettings.PrivacyChoices.HIDE,
        )

    def setUp(self):
        self.client.force_authenticate(self.user)

    def test_retrieve_users(self):
        for user in [self.public_user, self.private_user, self.org_user, self.user]:
            response = self.client.get(
                reverse("ProjectUser-detail", args=(user.keycloak_id,))
            )
            self.assertEqual(response.status_code, 200)

    def test_list_users(self):
        response = self.client.get(reverse("ProjectUser-list"))
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 4)
        self.assertEqual(
            {user["id"] for user in content},
            {self.public_user.id, self.user.id, self.org_user.id, self.private_user.id},
        )

    def test_view_project_members(self):
        response = self.client.get(reverse("Project-detail", args=(self.project.pk,)))
        self.assertEqual(response.status_code, 200)
        content = response.json()
        self.assertEqual(len(content["team"]["members"]), 3)
        self.assertEqual(
            {user["id"] for user in content["team"]["members"]},
            {self.public_user.id, self.org_user.id, self.private_user.id},
        )

    def test_view_people_group_members(self):
        response = self.client.get(
            reverse(
                "PeopleGroup-member",
                args=(
                    self.people_group.organization.code,
                    self.people_group.pk,
                ),
            )
        )
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 3)
        self.assertEqual(
            {user["id"] for user in content},
            {self.public_user.id, self.org_user.id, self.private_user.id},
        )

    def test_view_users_in_comments(self):
        public_comment = CommentFactory(author=self.public_user, project=self.project)
        private_comment = CommentFactory(author=self.private_user, project=self.project)
        org_comment = CommentFactory(author=self.org_user, project=self.project)
        response = self.client.get(reverse("Comment-list", args=[self.project.id]))
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 3)
        self.assertEqual(
            {(comment["author"]["id"], comment["id"]) for comment in content},
            {
                (self.public_user.id, public_comment.id),
                (self.private_user.id, private_comment.id),
                (self.org_user.id, org_comment.id),
            },
        )

    def test_view_users_in_follows(self):
        public_follow = FollowFactory(follower=self.public_user, project=self.project)
        private_follow = FollowFactory(follower=self.private_user, project=self.project)
        org_follow = FollowFactory(follower=self.org_user, project=self.project)
        response = self.client.get(reverse("Followed-list", args=(self.project.id,)))
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 3)
        self.assertEqual(
            {(follow["follower"]["id"], follow["id"]) for follow in content},
            {
                (self.public_user.id, public_follow.id),
                (self.private_user.id, private_follow.id),
                (self.org_user.id, org_follow.id),
            },
        )

    def test_view_users_in_reviews(self):
        public_review = ReviewFactory(reviewer=self.public_user, project=self.project)
        private_review = ReviewFactory(reviewer=self.private_user, project=self.project)
        org_review = ReviewFactory(reviewer=self.org_user, project=self.project)
        response = self.client.get(reverse("Reviewed-list", args=(self.project.id,)))
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 3)
        self.assertEqual(
            {(review["reviewer"]["id"], review["id"]) for review in content},
            {
                (self.public_user.id, public_review.id),
                (self.private_user.id, private_review.id),
                (self.org_user.id, org_review.id),
            },
        )

    def test_view_users_in_invitations(self):
        public_invitation = InvitationFactory(
            owner=self.public_user, organization=self.organization
        )
        private_invitation = InvitationFactory(
            owner=self.private_user, organization=self.organization
        )
        org_invitation = InvitationFactory(
            owner=self.org_user, organization=self.organization
        )
        response = self.client.get(
            reverse("Invitation-list", args=(self.organization.code,))
        )
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 3)
        self.assertEqual(
            {(invitation["owner"]["id"], invitation["id"]) for invitation in content},
            {
                (self.public_user.id, public_invitation.id),
                (self.private_user.id, private_invitation.id),
                (self.org_user.id, org_invitation.id),
            },
        )

    def test_view_users_in_notifications(self):
        public_notification = NotificationFactory(
            receiver=self.user, sender=self.public_user
        )
        private_notification = NotificationFactory(
            receiver=self.user, sender=self.private_user
        )
        org_notification = NotificationFactory(receiver=self.user, sender=self.org_user)
        response = self.client.get(reverse("Notification-list"))
        self.assertEqual(response.status_code, 200)
        content = response.json()["results"]
        self.assertEqual(len(content), 3)
        self.assertEqual(
            {
                (notification["sender"]["id"], notification["id"])
                for notification in content
            },
            {
                (self.public_user.id, public_notification.id),
                (self.private_user.id, private_notification.id),
                (self.org_user.id, org_notification.id),
            },
        )
