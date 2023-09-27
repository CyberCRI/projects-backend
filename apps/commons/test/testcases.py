import logging
from typing import Optional

from django.db import models
from django.test import SimpleTestCase
from rest_framework.test import APITestCase

from apps.accounts.factories import UserFactory
from apps.accounts.models import PeopleGroup
from apps.accounts.utils import get_superadmins_group
from apps.organizations.factories import OrganizationFactory
from apps.organizations.models import Organization
from apps.projects.models import Project

from .client import JwtClient
from .mixins import GetImageTestCaseMixin


class JwtTestCaseMixin(
    SimpleTestCase,
    GetImageTestCaseMixin,
):
    """Modify the default client to use JwtClient."""

    client: JwtClient

    client_class = JwtClient

    @classmethod
    def setUpClass(cls):
        """Disable logging while testing."""
        super().setUpClass()
        logging.disable(logging.CRITICAL)

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()  # noqa
        cls.organization = OrganizationFactory()
        cls.test_image = cls.get_test_image()

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


class JwtAPITestCase(JwtTestCaseMixin, APITestCase):
    """`APITestCase` using `JwtClient`."""

    def get_parameterized_test_user(
        self,
        role,
        owned_instance: Optional[models.Model] = None,
        project: Optional[Project] = None,
        people_group: Optional[PeopleGroup] = None,
        organization: Optional[Organization] = None,
    ):
        if (
            sum([1 for obj in [project, organization, people_group] if obj is not None])
            > 1
        ):
            raise ValueError(
                "You can't give more than one project, organization or people group"
            )
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
        if organization and role == TestRoles.ORG_ADMIN:
            return UserFactory(groups=[organization.get_admins()])
        if organization and role == TestRoles.ORG_FACILITATOR:
            return UserFactory(groups=[organization.get_facilitators()])
        if organization and role == TestRoles.ORG_USER:
            return UserFactory(groups=[organization.get_users()])
        # people group roles
        if people_group and role == TestRoles.GROUP_LEADER:
            return UserFactory(groups=[people_group.get_leaders()])
        if people_group and role == TestRoles.GROUP_MANAGER:
            return UserFactory(groups=[people_group.get_managers()])
        if people_group and role == TestRoles.GROUP_MEMBER:
            return UserFactory(groups=[people_group.get_members()])
        if people_group and role == TestRoles.ORG_ADMIN:
            return UserFactory(groups=[people_group.organization.get_admins()])
        if people_group and role == TestRoles.ORG_FACILITATOR:
            return UserFactory(groups=[people_group.organization.get_facilitators()])
        if people_group and role == TestRoles.ORG_USER:
            return UserFactory(groups=[people_group.organization.get_users()])
        # project roles
        if project and role == TestRoles.PROJECT_OWNER:
            return UserFactory(groups=[project.get_owners()])
        if project and role == TestRoles.PROJECT_REVIEWER:
            return UserFactory(groups=[project.get_reviewers()])
        if project and role == TestRoles.PROJECT_MEMBER:
            return UserFactory(groups=[project.get_members()])
        if project and role == TestRoles.ORG_ADMIN:
            return UserFactory(
                groups=[o.get_admins() for o in project.organizations.all()]
            )
        if project and role == TestRoles.ORG_FACILITATOR:
            return UserFactory(
                groups=[o.get_facilitators() for o in project.organizations.all()]
            )
        if project and role == TestRoles.ORG_USER:
            return UserFactory(
                groups=[o.get_users() for o in project.organizations.all()]
            )
        raise ValueError(f"Invalid role {role} for given object(s)")


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
