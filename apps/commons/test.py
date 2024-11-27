import base64
import logging
import os
import uuid
from typing import Dict, List, Optional
from unittest import skipUnless, util

from django.conf import settings
from django.core.files import File
from django.db import models
from faker import Faker
from rest_framework.test import APIClient, APITestCase

from apps.accounts.authentication import BearerToken
from apps.accounts.factories import UserFactory
from apps.accounts.models import PeopleGroup, ProjectUser
from apps.accounts.utils import get_superadmins_group
from apps.files.models import Image
from apps.organizations.models import Organization
from apps.projects.models import Project

from .exceptions import ExceptionType

util._MAX_LENGTH = 1000000
faker = Faker()


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


class JwtClient(APIClient):
    """Override default `Client` to create a JWT token when `force_login()`.

    This token will then be given in any subsequent request in the
    header `HTTP_AUTHORIZATION`.
    """

    def force_authenticate(  # nosec
        self,
        user: ProjectUser = None,
        token: str = None,
        token_type: str = "JWT",
        through_cookie=False,
    ):
        """Login the given user by creating a JWT token."""
        if user:
            if token is None:
                token = BearerToken.for_user(user)
            if through_cookie:
                self.cookies[settings.JWT_ACCESS_TOKEN_COOKIE_NAME] = token
            else:
                self.credentials(HTTP_AUTHORIZATION=f"{token_type} {token}")
        elif token:
            self.credentials(HTTP_AUTHORIZATION=f"{token_type} {token}")


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

    @classmethod
    def get_parameterized_test_user(
        cls,
        role,
        instances: Optional[List[models.Model]] = None,
        owned_instance: Optional[models.Model] = None,
    ):
        if instances:
            instances_type = set([type(instance) for instance in instances])
            if len(instances_type) > 1:
                instances_types = ", ".join([str(t) for t in instances_type])
                raise ValueError(
                    f"All instances must be of the same type. Got {instances_types}"
                )
        if not owned_instance and role == TestRoles.OWNER:
            raise ValueError("Owned instance must be provided for OWNER role")
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
        if isinstance(instances[0], Organization):
            if role == TestRoles.ORG_ADMIN:
                return UserFactory(groups=[o.get_admins() for o in instances])
            if role == TestRoles.ORG_FACILITATOR:
                return UserFactory(groups=[o.get_facilitators() for o in instances])
            if role == TestRoles.ORG_USER:
                return UserFactory(groups=[o.get_users() for o in instances])
        # people group roles
        if isinstance(instances[0], PeopleGroup):
            if role == TestRoles.GROUP_LEADER:
                return UserFactory(groups=[p.get_leaders() for p in instances])
            if role == TestRoles.GROUP_MANAGER:
                return UserFactory(groups=[p.get_managers() for p in instances])
            if role == TestRoles.GROUP_MEMBER:
                return UserFactory(groups=[p.get_members() for p in instances])
            if role == TestRoles.ORG_ADMIN:
                return UserFactory(
                    groups=[p.organization.get_admins() for p in instances]
                )
            if role == TestRoles.ORG_FACILITATOR:
                return UserFactory(
                    groups=[p.organization.get_facilitators() for p in instances]
                )
            if role == TestRoles.ORG_USER:
                return UserFactory(
                    groups=[p.organization.get_users() for p in instances]
                )
        # project roles
        if isinstance(instances[0], Project):
            if role == TestRoles.PROJECT_OWNER:
                return UserFactory(groups=[p.get_owners() for p in instances])
            if role == TestRoles.PROJECT_REVIEWER:
                return UserFactory(groups=[p.get_reviewers() for p in instances])
            if role == TestRoles.PROJECT_MEMBER:
                return UserFactory(groups=[p.get_members() for p in instances])
            if role == TestRoles.ORG_ADMIN:
                return UserFactory(
                    groups=[
                        o.get_admins()
                        for o in Organization.objects.filter(projects__in=instances)
                    ]
                )
            if role == TestRoles.ORG_FACILITATOR:
                return UserFactory(
                    groups=[
                        o.get_facilitators()
                        for o in Organization.objects.filter(projects__in=instances)
                    ]
                )
            if role == TestRoles.ORG_USER:
                return UserFactory(
                    groups=[
                        o.get_users()
                        for o in Organization.objects.filter(projects__in=instances)
                    ]
                )
        raise ValueError(f"Invalid role {role} for given object(s)")

    @classmethod
    def get_test_image_file(cls) -> File:
        """Return a dummy test image file."""
        return File(
            open(f"{settings.STATIC_ROOT}/test_image.png", "rb")  # noqa: SIM115
        )

    @classmethod
    def get_oversized_test_image_file(cls) -> File:
        """Return a dummy test image file."""
        return File(
            open(  # noqa: SIM115
                f"{settings.STATIC_ROOT}/oversized_test_image.jpg", "rb"
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

    def assertApiValidationError(  # noqa: N802
        self, response, messages: Optional[Dict[str, List[str]]] = None
    ):
        content = response.json()
        self.assertEqual(content["type"], ExceptionType.VALIDATION.value)
        if messages:
            self.assertEqual(content["errors"], messages)

    def assertApiPermissionError(  # noqa: N802
        self, response, detail: Optional[str] = None
    ):
        content = response.json()
        self.assertEqual(content["type"], ExceptionType.PERMISSION.value)
        if detail:
            self.assertEqual(content["detail"], detail)

    def assertApiTechnicalError(  # noqa: N802
        self, response, detail: Optional[str] = None
    ):
        content = response.json()
        self.assertEqual(content["type"], ExceptionType.TECHNICAL.value)
        if detail:
            self.assertEqual(content["detail"], detail)

    def assertApiAuthenticationError(  # noqa: N802
        self, response, detail: Optional[str] = None
    ):
        content = response.json()
        self.assertEqual(content["type"], ExceptionType.AUTHENTHICATION.value)
        if detail:
            self.assertEqual(content["detail"], detail)


def skipUnlessSearch(decorated):  # noqa: N802
    """Skip decorated tests if ennvar `TEST_SEARCH` has not been set to 1."""
    check = bool(int(os.getenv("TEST_SEARCH", 0)))
    msg = "Search test skipped, use envvar 'TEST_SEARCH=1' to test"
    return skipUnless(check, msg)(decorated)


def skipUnlessGoogle(decorated):  # noqa: N802
    """Skip decorated tests if ennvar `TEST_GOOGLE` has not been set to 1."""
    check = bool(int(os.getenv("TEST_GOOGLE", 0)))
    msg = "Google test skipped, use envvar 'TEST_GOOGLE=1' to test"
    return skipUnless(check, msg)(decorated)
