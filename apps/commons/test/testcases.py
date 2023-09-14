import logging
from typing import Optional, Union

from django.db import models
from django.test import SimpleTestCase
from rest_framework.test import APITestCase

from apps.accounts.factories import UserFactory
from apps.accounts.models import PeopleGroup
from apps.accounts.utils import get_superadmins_group
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


class UserRoles(models.TextChoices):
    ANONYMOUS = "anonymous"
    DEFAULT = "default"
    SUPERADMIN = "superadmin"
    ORGANIZATION_ADMIN = "organization_admin"
    ORGANIZATION_FACILITATOR = "organization_facilitator"
    ORGANIZATION_USER = "organization_user"
    PEOPLE_GROUP_LEADER = "people_group_leader"
    PEOPLE_GROUP_MANAGER = "people_group_manager"
    PEOPLE_GROUP_MEMBER = "people_group_member"
    PROJECT_OWNER = "project_owner"
    PROJECT_REVIEWER = "project_reviewer"
    PROJECT_MEMBER = "project_member"


class JwtAPITestCase(JwtTestCaseMixin, APITestCase):
    """`APITestCase` using `JwtClient`."""

    def get_test_user(
        self,
        role,
        instance: Optional[Union[Organization, Project, PeopleGroup]] = None,
    ):
        instance_type = type(instance)
        # base roles
        if role == UserRoles.ANONYMOUS:
            return None
        if role == UserRoles.DEFAULT:
            return UserFactory()
        if role == UserRoles.SUPERADMIN:
            return UserFactory(groups=[get_superadmins_group()])
        # organization roles
        if role == UserRoles.ORGANIZATION_ADMIN and instance_type == Organization:
            return UserFactory(groups=[instance.get_admins()])
        if role == UserRoles.ORGANIZATION_FACILITATOR and instance_type == Organization:
            return UserFactory(groups=[instance.get_facilitators()])
        if role == UserRoles.ORGANIZATION_USER and instance_type == Organization:
            return UserFactory(groups=[instance.get_users()])
        # people group roles
        if role == UserRoles.PEOPLE_GROUP_LEADER and instance_type == PeopleGroup:
            return UserFactory(groups=[instance.get_leaders()])
        if role == UserRoles.PEOPLE_GROUP_MANAGER and instance_type == PeopleGroup:
            return UserFactory(groups=[instance.get_managers()])
        if role == UserRoles.PEOPLE_GROUP_MEMBER and instance_type == PeopleGroup:
            return UserFactory(groups=[instance.get_members()])
        if role == UserRoles.ORGANIZATION_ADMIN and instance_type == PeopleGroup:
            return UserFactory(groups=[instance.organization.get_admins()])
        if role == UserRoles.ORGANIZATION_FACILITATOR and instance_type == PeopleGroup:
            return UserFactory(groups=[instance.organization.get_facilitators()])
        if role == UserRoles.ORGANIZATION_USER and instance_type == PeopleGroup:
            return UserFactory(groups=[instance.organization.get_users()])
        # project roles
        if role == UserRoles.PROJECT_OWNER and instance_type == Project:
            return UserFactory(groups=[instance.get_owners()])
        if role == UserRoles.PROJECT_REVIEWER and instance_type == Project:
            return UserFactory(groups=[instance.get_reviewers()])
        if role == UserRoles.PROJECT_MEMBER and instance_type == Project:
            return UserFactory(groups=[instance.get_members()])
        if role == UserRoles.ORGANIZATION_ADMIN and instance_type == Project:
            return UserFactory(
                groups=[o.get_admins() for o in instance.organizations.all()]
            )
        if role == UserRoles.ORGANIZATION_FACILITATOR and instance_type == Project:
            return UserFactory(
                groups=[o.get_facilitators() for o in instance.organizations.all()]
            )
        if role == UserRoles.ORGANIZATION_USER and instance_type == Project:
            return UserFactory(
                groups=[o.get_users() for o in instance.organizations.all()]
            )
        raise ValueError(f"Invalid role {role} for instance type {instance_type}")


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
