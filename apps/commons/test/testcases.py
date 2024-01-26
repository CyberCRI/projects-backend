import base64
import logging
import random
import uuid
from typing import List, Optional

from django.conf import settings
from django.core.files import File
from django.db import models
from faker import Faker
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.factories import UserFactory
from apps.accounts.models import PeopleGroup
from apps.accounts.utils import get_superadmins_group
from apps.files.models import Image
from apps.organizations.models import Organization
from apps.projects.models import Project

from .client import JwtClient

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


class TagTestCaseMixin:
    class QueryWikipediaMockResponse:
        def __init__(self, status_code: int):
            self.status_code = status_code
            self.wikipedia_qid = TagTestCaseMixin.get_random_wikipedia_qid()
            self.pageid = faker.pyint()
            self.title = faker.word()
            self.link_title = faker.word()
            self.extract = faker.sentence()

        def json(self):
            return {
                "warnings": None,
                "fr": [
                    {
                        "pageid": self.pageid,
                        "ns": 0,
                        "title": self.title,
                        "index": 1,
                        "pageprops": {"wikibase_item": self.wikipedia_qid},
                        "links": [
                            {"ns": 0, "title": self.link_title},
                        ],
                        "extract": self.extract,
                    }
                ],
            }

    class GetWikipediaTagMocked:
        def __init__(self, qid: str, status_code: int, en: bool, fr: bool):
            self.qid = qid
            self.status_code = status_code
            self.en = en
            self.fr = fr

        def json(self):
            labels = {
                "en": {"language": "en", "value": f"name_en_{self.qid}"},
                "fr": {"language": "fr", "value": f"name_fr_{self.qid}"},
            }
            descriptions = {
                "en": {"language": "en", "value": f"description_en_{self.qid}"},
                "fr": {"language": "fr", "value": f"description_fr_{self.qid}"},
            }
            if not self.en:
                del labels["en"]
                del descriptions["en"]
            if not self.fr:
                del labels["fr"]
                del descriptions["fr"]
            return {
                "entities": {
                    self.qid: {
                        "labels": labels,
                        "descriptions": descriptions,
                    }
                }
            }

    @classmethod
    def get_random_wikipedia_qid(cls):
        return f"Q{random.randint(100000, 999999)}"  # nosec

    @classmethod
    def get_wikipedia_tag_mocked_return(
        cls,
        qid: str,
        status_code: int = status.HTTP_200_OK,
        en: bool = True,
        fr: bool = True,
    ):
        return cls.GetWikipediaTagMocked(qid, status_code, en, fr)

    @classmethod
    def get_wikipedia_tag_mocked_side_effect(cls, qid, *args, **kwargs):
        return cls.get_wikipedia_tag_mocked_return(qid)

    @classmethod
    def query_wikipedia_mocked_return(cls, status_code: int = status.HTTP_200_OK):
        return cls.QueryWikipediaMockResponse(status_code)
