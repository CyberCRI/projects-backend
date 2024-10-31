from django.urls import reverse
from faker import Faker
from rest_framework import status

from apps.accounts.factories import PeopleGroupFactory, UserFactory
from apps.accounts.utils import get_superadmins_group
from apps.announcements.factories import AnnouncementFactory
from apps.commons.test import JwtAPITestCase
from apps.feedbacks.factories import CommentFactory, FollowFactory, ReviewFactory
from apps.files.factories import AttachmentFileFactory, AttachmentLinkFactory
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import (
    BlogEntryFactory,
    GoalFactory,
    LinkedProjectFactory,
    LocationFactory,
    ProjectFactory,
    ProjectMessageFactory,
)
from apps.skills.factories import SkillFactory

faker = Faker()


class MultipleLookupsTestCase(JwtAPITestCase):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.superadmin = UserFactory(groups=[get_superadmins_group()])
        cls.user = UserFactory(profile_picture=cls.get_test_image())
        cls.organization = OrganizationFactory()
        cls.project = ProjectFactory(
            organizations=[cls.organization],
            header_image=cls.get_test_image(),
        )
        cls.people_group = PeopleGroupFactory(
            organization=cls.organization,
            header_image=cls.get_test_image(),
            logo_image=cls.get_test_image(),
        )

    def test_people_group_multiple_lookups(self):
        self.client.force_authenticate(self.superadmin)
        response = self.client.get(
            reverse(
                "PeopleGroup-detail",
                args=(self.organization.code, self.people_group.pk),
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.people_group.id)
        response = self.client.get(
            reverse(
                "PeopleGroup-detail",
                args=(self.organization.code, self.people_group.slug),
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.people_group.id)

    def test_people_group_header_multiple_lookups(self):
        self.client.force_authenticate(self.superadmin)
        payload = {
            "scale_x": faker.pyfloat(min_value=1.0, max_value=2.0),
        }
        response = self.client.patch(
            reverse(
                "PeopleGroup-header-list",
                args=(self.organization.code, self.people_group.id),
            ),
            data=payload,
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["id"], self.people_group.header_image.id)
        response = self.client.patch(
            reverse(
                "PeopleGroup-header-list",
                args=(self.organization.code, self.people_group.slug),
            ),
            data=payload,
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["id"], self.people_group.header_image.id)

    def test_people_group_logo_multiple_lookups(self):
        self.client.force_authenticate(self.superadmin)
        payload = {
            "scale_x": faker.pyfloat(min_value=1.0, max_value=2.0),
        }
        response = self.client.patch(
            reverse(
                "PeopleGroup-logo-list",
                args=(self.organization.code, self.people_group.id),
            ),
            data=payload,
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["id"], self.people_group.logo_image.id)
        response = self.client.patch(
            reverse(
                "PeopleGroup-logo-list",
                args=(self.organization.code, self.people_group.slug),
            ),
            data=payload,
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["id"], self.people_group.logo_image.id)

    def test_user_multiple_lookups(self):
        self.client.force_authenticate(self.superadmin)
        response = self.client.get(reverse("ProjectUser-detail", args=(self.user.id,)))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["id"], self.user.id)
        response = self.client.get(
            reverse("ProjectUser-detail", args=(self.user.slug,))
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["id"], self.user.id)
        response = self.client.get(
            reverse("ProjectUser-detail", args=(self.user.keycloak_id,))
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["id"], self.user.id)

    def test_user_privacy_settings_multiple_lookups(self):
        self.client.force_authenticate(self.superadmin)
        response = self.client.get(
            reverse("PrivacySettings-detail", args=(self.user.id,))
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["id"], self.user.privacy_settings.id)
        response = self.client.get(
            reverse("PrivacySettings-detail", args=(self.user.slug,))
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["id"], self.user.privacy_settings.id)
        response = self.client.get(
            reverse("PrivacySettings-detail", args=(self.user.keycloak_id,))
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["id"], self.user.privacy_settings.id)

    def test_user_notification_settings_multiple_lookups(self):
        self.client.force_authenticate(self.superadmin)
        response = self.client.get(
            reverse("NotificationSettings-detail", args=(self.user.id,))
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["id"], self.user.notification_settings.id)
        response = self.client.get(
            reverse("NotificationSettings-detail", args=(self.user.slug,))
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["id"], self.user.notification_settings.id)
        response = self.client.get(
            reverse("NotificationSettings-detail", args=(self.user.keycloak_id,))
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["id"], self.user.notification_settings.id)

    def test_user_profile_picture_multiple_lookups(self):
        self.client.force_authenticate(self.superadmin)
        payload = {
            "scale_x": faker.pyfloat(min_value=1.0, max_value=2.0),
        }
        response = self.client.patch(
            reverse(
                "UserProfilePicture-detail",
                args=(self.user.id, self.user.profile_picture.id),
            ),
            data=payload,
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["id"], self.user.profile_picture.id)
        response = self.client.patch(
            reverse(
                "UserProfilePicture-detail",
                args=(self.user.slug, self.user.profile_picture.id),
            ),
            data=payload,
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["id"], self.user.profile_picture.id)
        response = self.client.patch(
            reverse(
                "UserProfilePicture-detail",
                args=(self.user.keycloak_id, self.user.profile_picture.id),
            ),
            data=payload,
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["id"], self.user.profile_picture.id)

    def test_skill_multiple_lookups(self):
        self.client.force_authenticate(self.superadmin)
        skill = SkillFactory()
        response = self.client.get(
            reverse("Skill-detail", args=(skill.user.id, skill.id))
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["id"], skill.id)
        response = self.client.get(
            reverse("Skill-detail", args=(skill.user.slug, skill.id))
        )
        content = response.json()
        self.assertEqual(content["id"], skill.id)
        response = self.client.get(
            reverse("Skill-detail", args=(skill.user.keycloak_id, skill.id))
        )
        content = response.json()
        self.assertEqual(content["id"], skill.id)

    def test_project_multiple_lookups(self):
        self.client.force_authenticate(self.superadmin)
        response = self.client.get(reverse("Project-detail", args=(self.project.id,)))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["id"], self.project.id)
        response = self.client.get(reverse("Project-detail", args=(self.project.slug,)))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["id"], self.project.id)

    def test_announcement_multiple_lookups(self):
        self.client.force_authenticate(self.superadmin)
        announcement = AnnouncementFactory(project=self.project)
        response = self.client.get(
            reverse(
                "Announcement-detail",
                args=(announcement.project.id, announcement.id),
            ),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["id"], announcement.id)
        response = self.client.get(
            reverse(
                "Announcement-detail",
                args=(announcement.project.slug, announcement.id),
            ),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["id"], announcement.id)

    def test_goal_multiple_lookups(self):
        self.client.force_authenticate(self.superadmin)
        goal = GoalFactory(project=self.project)
        response = self.client.get(
            reverse("Goal-detail", args=(goal.project.id, goal.id)),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["id"], goal.id)
        response = self.client.get(
            reverse("Goal-detail", args=(goal.project.slug, goal.id)),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["id"], goal.id)

    def test_project_header_multiple_lookups(self):
        self.client.force_authenticate(self.superadmin)
        payload = {
            "scale_x": faker.pyfloat(min_value=1.0, max_value=2.0),
        }
        response = self.client.patch(
            reverse(
                "Project-header-detail",
                args=(self.project.id, self.project.header_image.id),
            ),
            data=payload,
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["id"], self.project.header_image.id)
        response = self.client.patch(
            reverse(
                "Project-header-detail",
                args=(self.project.slug, self.project.header_image.id),
            ),
            data=payload,
            format="multipart",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["id"], self.project.header_image.id)

    def test_location_multiple_lookups(self):
        self.client.force_authenticate(self.superadmin)
        location = LocationFactory(project=self.project)
        response = self.client.get(
            reverse("Location-detail", args=(location.project.id, location.id)),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["id"], location.id)
        response = self.client.get(
            reverse("Location-detail", args=(location.project.slug, location.id)),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["id"], location.id)

    def test_linked_project_multiple_lookups(self):
        self.client.force_authenticate(self.superadmin)
        project = ProjectFactory(organizations=[self.organization])
        linked_project = LinkedProjectFactory(target=project, project=self.project)
        response = self.client.delete(
            reverse(
                "LinkedProjects-detail",
                args=(linked_project.target.id, linked_project.id),
            ),
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        linked_project = LinkedProjectFactory(target=project, project=self.project)
        response = self.client.delete(
            reverse(
                "LinkedProjects-detail",
                args=(linked_project.target.slug, linked_project.id),
            ),
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_attachment_file_multiple_lookups(self):
        self.client.force_authenticate(self.superadmin)
        file = AttachmentFileFactory(project=self.project)
        response = self.client.get(
            reverse("AttachmentFile-detail", args=(file.project.id, file.id)),
        )
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        response = self.client.get(
            reverse("AttachmentFile-detail", args=(file.project.slug, file.id)),
        )
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)

    def test_attachment_link_multiple_lookups(self):
        self.client.force_authenticate(self.superadmin)
        link = AttachmentLinkFactory(project=self.project)
        response = self.client.get(
            reverse("AttachmentLink-detail", args=(link.project.id, link.id)),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["id"], link.id)
        response = self.client.get(
            reverse("AttachmentLink-detail", args=(link.project.slug, link.id)),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["id"], link.id)

    def test_project_images_multiple_lookups(self):
        self.client.force_authenticate(self.superadmin)
        image = self.get_test_image(owner=self.user)
        self.project.images.add(image)
        response = self.client.get(
            reverse("Project-images-detail", args=(self.project.id, image.id)),
        )
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        response = self.client.get(
            reverse("Project-images-detail", args=(self.project.slug, image.id)),
        )
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)

    def test_blog_entry_multiple_lookups(self):
        self.client.force_authenticate(self.superadmin)
        blog_entry = BlogEntryFactory(project=self.project)
        response = self.client.get(
            reverse("BlogEntry-detail", args=(blog_entry.project.id, blog_entry.id)),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["id"], blog_entry.id)
        response = self.client.get(
            reverse("BlogEntry-detail", args=(blog_entry.project.slug, blog_entry.id)),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["id"], blog_entry.id)

    def test_blog_entry_images_multiple_lookups(self):
        self.client.force_authenticate(self.superadmin)
        blog_entry = BlogEntryFactory(project=self.project)
        image = self.get_test_image(owner=self.user)
        blog_entry.images.add(image)
        response = self.client.get(
            reverse("BlogEntry-images-detail", args=(blog_entry.project.id, image.id)),
        )
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        response = self.client.get(
            reverse(
                "BlogEntry-images-detail", args=(blog_entry.project.slug, image.id)
            ),
        )
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)

    def test_project_message_multiple_lookups(self):
        self.client.force_authenticate(self.superadmin)
        project_message = ProjectMessageFactory(project=self.project, author=self.user)
        response = self.client.get(
            reverse(
                "ProjectMessage-detail",
                args=(project_message.project.id, project_message.id),
            ),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["id"], project_message.id)
        response = self.client.get(
            reverse(
                "ProjectMessage-detail",
                args=(project_message.project.slug, project_message.id),
            ),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["id"], project_message.id)

    def test_project_message_images_multiple_lookups(self):
        self.client.force_authenticate(self.superadmin)
        project_message = ProjectMessageFactory(project=self.project, author=self.user)
        image = self.get_test_image(owner=self.user)
        project_message.images.add(image)
        response = self.client.get(
            reverse(
                "ProjectMessage-images-detail",
                args=(project_message.project.id, image.id),
            ),
        )
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        response = self.client.get(
            reverse(
                "ProjectMessage-images-detail",
                args=(project_message.project.slug, image.id),
            ),
        )
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)

    def test_comment_multiple_lookups(self):
        self.client.force_authenticate(self.superadmin)
        comment = CommentFactory(project=self.project, author=self.user)
        response = self.client.get(
            reverse("Comment-detail", args=(comment.project.id, comment.id)),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["id"], comment.id)
        response = self.client.get(
            reverse("Comment-detail", args=(comment.project.slug, comment.id)),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["id"], comment.id)

    def test_comment_images_multiple_lookups(self):
        self.client.force_authenticate(self.superadmin)
        comment = CommentFactory(project=self.project, author=self.user)
        image = self.get_test_image(owner=self.user)
        comment.images.add(image)
        response = self.client.get(
            reverse("Comment-images-detail", args=(comment.project.id, image.id)),
        )
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        response = self.client.get(
            reverse("Comment-images-detail", args=(comment.project.slug, image.id)),
        )
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)

    def test_follow_multiple_lookups(self):
        self.client.force_authenticate(self.superadmin)
        follow = FollowFactory(project=self.project, follower=self.user)
        response = self.client.get(
            reverse("Followed-list", args=(follow.project.id,)),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(content[0]["id"], follow.id)
        response = self.client.get(
            reverse("Followed-list", args=(follow.project.slug,)),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(content[0]["id"], follow.id)
        response = self.client.get(
            reverse("Follower-list", args=(follow.follower.id,)),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(content[0]["id"], follow.id)
        response = self.client.get(
            reverse("Follower-list", args=(follow.follower.slug,)),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(content[0]["id"], follow.id)
        response = self.client.get(
            reverse("Follower-list", args=(follow.follower.keycloak_id,)),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()["results"]
        self.assertEqual(content[0]["id"], follow.id)

    def test_review_multiple_lookups(self):
        self.client.force_authenticate(self.superadmin)
        review = ReviewFactory(project=self.project, reviewer=self.user)
        response = self.client.get(
            reverse("Reviewed-detail", args=(review.project.id, review.id)),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["id"], review.id)
        response = self.client.get(
            reverse("Reviewed-detail", args=(review.project.slug, review.id)),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["id"], review.id)
        response = self.client.get(
            reverse("Reviewer-detail", args=(review.reviewer.id, review.id)),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["id"], review.id)
        response = self.client.get(
            reverse("Reviewer-detail", args=(review.reviewer.slug, review.id)),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["id"], review.id)
        response = self.client.get(
            reverse("Reviewer-detail", args=(review.reviewer.keycloak_id, review.id)),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.json()
        self.assertEqual(content["id"], review.id)

    def test_project_recommended_projects_multiple_lookups(self):
        self.client.force_authenticate(self.superadmin)
        response = self.client.get(
            reverse(
                "RecommendedProjects-for-project",
                args=(self.organization.code, self.project.id),
            ),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.client.get(
            reverse(
                "RecommendedProjects-for-project",
                args=(self.organization.code, self.project.slug),
            ),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_project_recommended_users_multiple_lookups(self):
        self.client.force_authenticate(self.superadmin)
        response = self.client.get(
            reverse(
                "RecommendedUsers-for-project",
                args=(self.organization.code, self.project.id),
            ),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.client.get(
            reverse(
                "RecommendedUsers-for-project",
                args=(self.organization.code, self.project.slug),
            ),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_mentoree_multiple_lookups(self):
        self.client.force_authenticate(self.superadmin)
        response = self.client.get(
            reverse(
                "UserMentorship-mentoree-candidate",
                args=(self.organization.code, self.user.id),
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.client.get(
            reverse(
                "UserMentorship-mentoree-candidate",
                args=(self.organization.code, self.user.slug),
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.client.get(
            reverse(
                "UserMentorship-mentoree-candidate",
                args=(self.organization.code, self.user.keycloak_id),
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_mentor_multiple_lookups(self):
        self.client.force_authenticate(self.superadmin)
        response = self.client.get(
            reverse(
                "UserMentorship-mentor-candidate",
                args=(self.organization.code, self.user.id),
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.client.get(
            reverse(
                "UserMentorship-mentor-candidate",
                args=(self.organization.code, self.user.slug),
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response = self.client.get(
            reverse(
                "UserMentorship-mentor-candidate",
                args=(self.organization.code, self.user.keycloak_id),
            )
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
