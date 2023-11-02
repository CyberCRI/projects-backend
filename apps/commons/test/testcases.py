import base64
import logging
import uuid
from typing import Optional

from django.conf import settings
from django.core.files import File
from django.db import models
from rest_framework.test import APITestCase

from apps.accounts.factories import UserFactory
from apps.accounts.models import PeopleGroup
from apps.accounts.utils import get_superadmins_group
from apps.files.models import Image
from apps.organizations.models import Organization
from apps.projects.models import Project

from .client import JwtClient


class TestRoles(models.TextChoices):
    ANONYMOUS = "anonymous"
    DEFAULT = "default"
    SUPERADMIN = "superadmin"
    ORG_ADMIN = "organization_admin"
    ORG_FACILITATOR = "organization_facilitator"
    ORG_USER = "organization_user"
    GROUP_LEADER = "people_group_leader"
    GROUP_MANAGER = "people_group_manager"
    GROUP_MEMBER = "people_group_member"
    PROJECT_OWNER = "project_owner"
    PROJECT_REVIEWER = "project_reviewer"
    PROJECT_MEMBER = "project_member"
    OWNER = "object_owner"


class JwtAPITestCase(APITestCase):
    """`APITestCase` using `JwtClient`."""

    client: JwtClient
    client_class = JwtClient

    @classmethod
    def setUpClass(cls):
        """Disable logging while testing."""
        super().setUpClass()
        logging.disable(logging.CRITICAL)

    @classmethod
    def tearDownClass(cls):
        """Re-enable logging after testing."""
        super().tearDownClass()
        logging.disable(logging.NOTSET)

    def tearDown(self):
        """Logout any authentication at the end of each test."""
        super().tearDown()
        self.client.logout()
        self.client.credentials()

    def get_parameterized_test_user(
        self,
        role,
        owned_instance: Optional[models.Model] = None,
        project: Optional[Project] = None,
        people_group: Optional[PeopleGroup] = None,
        organization: Optional[Organization] = None,
        projects: Optional[list[Project]] = None,
        people_groups: Optional[list[PeopleGroup]] = None,
        organizations: Optional[list[Organization]] = None,
    ):
        if (
            sum(
                [
                    1
                    for obj in [
                        project,
                        organization,
                        people_group,
                        projects,
                        organizations,
                        people_groups,
                    ]
                    if obj is not None
                ]
            )
            > 1
        ):
            raise ValueError(
                "You can't give more than one project, organization or people group"
            )
        if organization:
            organizations = [organization]
        if people_group:
            people_groups = [people_group]
        if project:
            projects = [project]
        # base roles
        if role == TestRoles.ANONYMOUS:
            return None
        if role == TestRoles.DEFAULT:
            return UserFactory()
        if role == TestRoles.SUPERADMIN:
            return UserFactory(groups=[get_superadmins_group()])
        # object owner roles
        if owned_instance and role == TestRoles.OWNER:
            return owned_instance.get_owner()
        # organization roles
        if organizations and role == TestRoles.ORG_ADMIN:
            return UserFactory(groups=[o.get_admins() for o in organizations])
        if organizations and role == TestRoles.ORG_FACILITATOR:
            return UserFactory(groups=[o.get_facilitators() for o in organizations])
        if organizations and role == TestRoles.ORG_USER:
            return UserFactory(groups=[o.get_users() for o in organizations])
        # people group roles
        if people_groups and role == TestRoles.GROUP_LEADER:
            return UserFactory(groups=[p.get_leaders() for p in people_groups])
        if people_groups and role == TestRoles.GROUP_MANAGER:
            return UserFactory(groups=[p.get_managers() for p in people_groups])
        if people_groups and role == TestRoles.GROUP_MEMBER:
            return UserFactory(groups=[p.get_members() for p in people_groups])
        if people_groups and role == TestRoles.ORG_ADMIN:
            return UserFactory(
                groups=[p.organization.get_admins() for p in people_groups]
            )
        if people_groups and role == TestRoles.ORG_FACILITATOR:
            return UserFactory(
                groups=[p.organization.get_facilitators() for p in people_groups]
            )
        if people_groups and role == TestRoles.ORG_USER:
            return UserFactory(
                groups=[p.organization.get_users() for p in people_groups]
            )
        # project roles
        if projects and role == TestRoles.PROJECT_OWNER:
            return UserFactory(groups=[p.get_owners() for p in projects])
        if projects and role == TestRoles.PROJECT_REVIEWER:
            return UserFactory(groups=[p.get_reviewers() for p in projects])
        if projects and role == TestRoles.PROJECT_MEMBER:
            return UserFactory(groups=[p.get_members() for p in projects])
        if projects and role == TestRoles.ORG_ADMIN:
            return UserFactory(
                groups=[
                    o.get_admins()
                    for o in Organization.objects.filter(projects__in=projects)
                ]
            )
        if projects and role == TestRoles.ORG_FACILITATOR:
            return UserFactory(
                groups=[
                    o.get_facilitators()
                    for o in Organization.objects.filter(projects__in=projects)
                ]
            )
        if projects and role == TestRoles.ORG_USER:
            return UserFactory(
                groups=[
                    o.get_users()
                    for o in Organization.objects.filter(projects__in=projects)
                ]
            )
        raise ValueError(f"Invalid role {role} for given object(s)")

    @classmethod
    def get_test_image_file(cls) -> File:
        """Return a dummy test image file."""
        return File(
            open(f"{settings.BASE_DIR}/assets/test_image.png", "rb")  # noqa: SIM115
        )

    @classmethod
    def get_oversized_test_image_file(cls) -> File:
        """Return a dummy test image file."""
        return File(
            open(  # noqa: SIM115
                f"{settings.BASE_DIR}/assets/oversized_test_image.jpg", "rb"
            )
        )

    @classmethod
    def get_test_image(cls, owner=None) -> Image:
        """Return an Image instance."""
        image = Image(name=str(uuid.uuid4()), file=cls.get_test_image_file())
        image._upload_to = lambda instance, filename: f"test/{uuid.uuid4()}"
        image.owner = owner if owner else UserFactory()
        image.save()
        return image

    @classmethod
    def get_base64_image(cls) -> str:
        return f'<img src="data:image/png;base64,{base64.b64encode(cls.get_test_image_file().read()).decode()}" alt=""/>'

    @classmethod
    def get_oversized_test_image(cls) -> Image:
        """Return an Image instance."""
        image = Image(name=str(uuid.uuid4()), file=cls.get_oversized_test_image_file())
        image._upload_to = lambda instance, filename: f"test/{uuid.uuid4()}"
        image.save()
        return image


class TagTestCase:
    class MockResponse:
        def __init__(self, **kwargs):
            self.dict = kwargs.pop("dict", {})

        def json(self):
            return self.dict

    def side_effect(self, qid, *args, **kwargs):
        results = {
            "Q1735684": {
                "name_en": "Kate Foo Kune en",
                "name_fr": "Kate Foo Kune fr",
                "name": "Kate Foo Kune default",
                "wikipedia_qid": "Q1735684",
            },
            "Q12335103": {
                "name_en": "Sharin Foo en",
                "name_fr": "Sharin Foo fr",
                "name": "Sharin Foo default",
                "wikipedia_qid": "Q12335103",
            },
            "Q3737270": {
                "name_en": "FOO en",
                "name_fr": "FOO fr",
                "name": "FOO default",
                "wikipedia_qid": "Q3737270",
            },
            "Q560361": {
                "name_fr": "brouillon",
                "name_en": "draft document",
                "name": "draft document",
                "wikipedia_qid": "Q560361",
            },
        }
        return self.MockResponse(dict=results[qid])
