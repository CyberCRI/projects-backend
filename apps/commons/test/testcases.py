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
    OWNER = "object_owner"


class JwtAPITestCase(JwtTestCaseMixin, APITestCase):
    """`APITestCase` using `JwtClient`."""

    def get_test_user(
        self,
        role,
        owned_instance: Optional[models.Model] = None,
        project: Optional[Project] = None,
        people_group: Optional[PeopleGroup] = None,
        organization: Optional[Organization] = None,
    ):
        if sum([1 for obj in [project, organization, people_group] if obj is not None]) > 1:
            raise ValueError(
                "You can't give more than one project, organization or people group"
            )
        # base roles
        if role == UserRoles.ANONYMOUS:
            return None
        if role == UserRoles.DEFAULT:
            return UserFactory()
        if role == UserRoles.SUPERADMIN:
            return UserFactory(groups=[get_superadmins_group()])
        # object owner roles
        if owned_instance:
            if role == UserRoles.OWNER:
                return owned_instance.get_owner()
        # organization roles
        if organization:
            if role == UserRoles.ORGANIZATION_ADMIN:
                return UserFactory(groups=[organization.get_admins()])
            if role == UserRoles.ORGANIZATION_FACILITATOR:
                return UserFactory(groups=[organization.get_facilitators()])
            if role == UserRoles.ORGANIZATION_USER:
                return UserFactory(groups=[organization.get_users()])
        # people group roles
        if people_group:
            if role == UserRoles.PEOPLE_GROUP_LEADER:
                return UserFactory(groups=[people_group.get_leaders()])
            if role == UserRoles.PEOPLE_GROUP_MANAGER:
                return UserFactory(groups=[people_group.get_managers()])
            if role == UserRoles.PEOPLE_GROUP_MEMBER:
                return UserFactory(groups=[people_group.get_members()])
            if role == UserRoles.ORGANIZATION_ADMIN:
                return UserFactory(groups=[people_group.organization.get_admins()])
            if role == UserRoles.ORGANIZATION_FACILITATOR:
                return UserFactory(groups=[people_group.organization.get_facilitators()])
            if role == UserRoles.ORGANIZATION_USER:
                return UserFactory(groups=[people_group.organization.get_users()])
        # project roles
        if project:
            if role == UserRoles.PROJECT_OWNER:
                return UserFactory(groups=[project.get_owners()])
            if role == UserRoles.PROJECT_REVIEWER:
                return UserFactory(groups=[project.get_reviewers()])
            if role == UserRoles.PROJECT_MEMBER:
                return UserFactory(groups=[project.get_members()])
            if role == UserRoles.ORGANIZATION_ADMIN:
                return UserFactory(
                    groups=[o.get_admins() for o in project.organizations.all()]
                )
            if role == UserRoles.ORGANIZATION_FACILITATOR:
                return UserFactory(
                    groups=[o.get_facilitators() for o in project.organizations.all()]
                )
            if role == UserRoles.ORGANIZATION_USER:
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
