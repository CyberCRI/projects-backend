import random
import uuid
from contextlib import suppress
from typing import Optional

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand
from django.db import IntegrityError
from django.utils import timezone
from faker import Faker

from apps.accounts.factories import (
    PeopleGroupFactory,
    SeedUserFactory,
    UserFactory,
    UserScoreFactory,
)
from apps.accounts.models import PeopleGroup, ProjectUser
from apps.announcements.factories import AnnouncementFactory
from apps.commons.models import GroupData
from apps.feedbacks.factories import CommentFactory, FollowFactory
from apps.files.factories import (
    AttachmentFileFactory,
    AttachmentLinkFactory,
    OrganizationAttachmentFileFactory,
)
from apps.files.models import Image
from apps.newsfeed.factories import EventFactory, InstructionFactory, NewsFactory
from apps.newsfeed.utils import init_newsfeed
from apps.organizations.factories import OrganizationFactory, ProjectCategoryFactory
from apps.organizations.models import Organization, ProjectCategory
from apps.projects.factories import (
    BlogEntryFactory,
    GoalFactory,
    LinkedProjectFactory,
    LocationFactory,
    ProjectFactory,
    ProjectMessageFactory,
)
from apps.projects.models import Stat
from apps.skills.factories import SkillFactory, TagClassificationFactory, TagFactory
from services.keycloak.interface import KeycloakService

faker = Faker()


class Command(BaseCommand):
    help = "Seed database"  # noqa: A003

    def add_arguments(self, parser):
        parser.add_argument(
            "--organization", "-o", type=str, required=True, help="Organization code."
        )
        parser.add_argument(
            "--url", "-u", type=str, required=True, help="Organization URL."
        )
        parser.add_argument(
            "--accounts",
            "-a",
            type=str,
            required=False,
            help=(
                "List of comma-separated accounts to create with format "
                "username:password:role. "
                "E.g. user1@exampel.com:pass1:admins,user2@example.com:pass2:users"
            ),
        )

    def create_image(
        self, upload_to: str, owner: Optional[ProjectUser] = None
    ) -> Image:
        image_data = faker.image((200, 200), image_format="jpeg")
        image = SimpleUploadedFile("image.jpg", image_data, content_type="image/jpeg")
        image_name = f"{uuid.uuid4()}.jpg"
        image = Image(name=image_name, file=image, owner=owner)
        image._upload_to = lambda instance, filename: f"{upload_to}/{image_name}"
        image.save()
        return image

    def create_account(self, account_str: str, organization: Organization) -> None:
        account_data = account_str.split(":")
        if len(account_data) != 3:
            raise ValueError(
                f"Invalid account format: {account_str}. Expected format: username:password:role"
            )
        username, password, role = account_data
        user_id = KeycloakService.service().get_user_id(username)
        if user_id:
            KeycloakService.service().delete_user(user_id)
        if role not in GroupData.organization_roles():
            raise ValueError(
                f"Invalid role: {role}. Must be one of {GroupData.organization_roles()}"
            )
        SeedUserFactory(
            email=username,
            personal_email=username,
            keycloak_account={
                "password": password,
                "email_verified": True,
            },
            groups=[organization.get_or_create_group(role)],
        )
        self.stdout.write(self.style.SUCCESS(f"Account created: {username}"))

    def handle(self, *args, **options):
        # Get or create the organization
        organization = OrganizationFactory(
            code=options["organization"],
            website_url=options["url"],
            logo_image=self.create_image(upload_to="organization/logo"),
            banner_image=self.create_image(upload_to="organization/banner"),
        )
        OrganizationAttachmentFileFactory(organization=organization)
        self.stdout.write(self.style.SUCCESS("Organization created."))

        # Create the admin user if credentials are provided
        if options.get("accounts"):
            accounts = options["accounts"].split(",")
            for account_str in accounts:
                self.create_account(account_str, organization)

        # Create the users
        for _ in range(50):
            user = UserFactory()
            image = self.create_image("account/profile", owner=user)
            user.profile_picture = image
            user.save()
            UserScoreFactory(user=user)
            organization.users.add(user)
        users = UserFactory.create_batch(size=50, groups=[organization.get_users()])
        self.stdout.write(self.style.SUCCESS("Users created."))

        # Create the groups
        root_people_group = PeopleGroup.update_or_create_root(organization)
        upper_level = [root_people_group]
        people_groups = []
        for _ in range(3):
            upper_level = [
                PeopleGroupFactory(
                    organization=organization,
                    parent=random.choice(upper_level),  # nosec B311
                    header_image=self.create_image(upload_to="people_group/header"),
                    logo_image=self.create_image(upload_to="people_group/logo"),
                )
                for _ in range(5)
            ]
            people_groups.extend(upper_level)
        self.stdout.write(self.style.SUCCESS("People groups created."))

        for people_group in people_groups:
            manager = random.choice(users)  # nosec B311
            members = [
                user
                for user in random.sample(users, k=random.randint(1, 5))  # nosec B311
                if user != manager
            ]
            people_group.managers.add(manager)
            people_group.members.add(*members)
        self.stdout.write(self.style.SUCCESS("People groups members added."))

        # Create the categories
        root_category = ProjectCategory.update_or_create_root(organization)
        upper_level = [root_category]
        categories = []
        for _ in range(3):
            upper_level = [
                ProjectCategoryFactory(
                    organization=organization,
                    parent=random.choice(upper_level),  # nosec B311
                )
                for _ in range(5)
            ]
            categories.extend(upper_level)
        self.stdout.write(self.style.SUCCESS("Project categories created."))

        # Create the tags and classifications
        tags = [TagFactory(organization=organization) for _ in range(60)]
        for i in range(3):
            TagClassificationFactory(
                organization=organization, tags=tags[i * 20 : (i + 1) * 20]
            )
        self.stdout.write(self.style.SUCCESS("Tags and classifications created."))

        # Create the newsfeed related objects
        date = timezone.localtime(timezone.now()) - timezone.timedelta(days=5)
        for _ in range(3):
            NewsFactory(
                organization=organization,
                people_groups=random.sample(  # nosec B311
                    people_groups, k=random.randint(1, 3)  # nosec B311
                ),
                publication_date=date,
            )
            NewsFactory(organization=organization, publication_date=date)
            InstructionFactory(
                organization=organization,
                people_groups=random.sample(  # nosec B311
                    people_groups, k=random.randint(1, 3)  # nosec B311
                ),
                publication_date=date,
            )
            InstructionFactory(organization=organization, publication_date=date)
            EventFactory(
                organization=organization,
                people_groups=random.sample(  # nosec B311
                    people_groups, k=random.randint(1, 3)  # nosec B311
                ),
                event_date=date,
            )
            EventFactory(organization=organization, event_date=date)
            date += timezone.timedelta(days=5)
        init_newsfeed()
        self.stdout.write(self.style.SUCCESS("Newsfeed items created."))

        for user in users:
            skills = random.sample(tags, k=random.randint(1, 10))  # nosec B311
            for skill in skills:
                SkillFactory(user=user, tag=skill)
        self.stdout.write(self.style.SUCCESS("Skills created."))

        # Create the projects and project related objects
        projects = [
            ProjectFactory(
                organizations=[organization],
                categories=[random.choice(categories)],  # nosec B311
                header_image=self.create_image(upload_to="project/header"),
            )
            for _ in range(50)
        ]
        self.stdout.write(self.style.SUCCESS("Projects created."))
        for _ in range(100):
            BlogEntryFactory(project=random.choice(projects))  # nosec B311
            GoalFactory(project=random.choice(projects))  # nosec B311
            CommentFactory(
                project=random.choice(projects),  # nosec B311
                author=random.choice(users),  # nosec B311
            )
            with suppress(IntegrityError):
                FollowFactory(
                    project=random.choice(projects),  # nosec B311
                    follower=random.choice(users),  # nosec B311
                )

        for _ in range(50):
            LocationFactory(project=random.choice(projects))  # nosec B311
            with suppress(IntegrityError):
                LinkedProjectFactory(
                    project=random.choice(projects[:25]),  # nosec B311
                    target=random.choice(projects[25:]),  # nosec B311
                )

        for _ in range(10):
            AnnouncementFactory(project=random.choice(projects))  # nosec B311

        for project in projects:
            stat = Stat(project=project)
            stat.update_all()
            AttachmentFileFactory(project=project)
            AttachmentLinkFactory(project=project)
            owner = random.choice(users)  # nosec B311
            members = [
                user
                for user in random.sample(users, k=random.randint(1, 5))  # nosec B311
                if user != owner
            ]
            project.owners.add(owner)
            project.members.add(*members)
            ProjectMessageFactory(
                project=project, author=random.choice([owner] + members)  # nosec B311
            )
        self.stdout.write(self.style.SUCCESS("Project related items created."))

        # expected by e2e frontend tests
        e2e_tag = TagFactory(
            organization=organization,
            title="Biology",
            title_en="Biology",
            title_fr="Biologie",
            description="Biology",
            description_en="Biology",
            description_fr="Biologie",
        )
        e2e_classification = TagClassificationFactory(
            organization=organization, tags=[e2e_tag]
        )
        organization.enabled_projects_tag_classifications.add(e2e_classification)
        organization.enabled_skills_tag_classifications.add(e2e_classification)
        self.stdout.write(self.style.SUCCESS("E2E frontend test tag created."))
