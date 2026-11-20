from parameterized import parameterized

from apps.accounts.factories import PeopleGroupFactory, UserFactory
from apps.accounts.models import AnonymousUser
from apps.commons.test import JwtAPITestCase, TestRoles
from apps.modules.base import _modules
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory, ProjectTabFactory
from services.crisalid.factories import (
    DocumentFactory,
    ResearcherFactory,
    StructureFactory,
)

ROLES = [
    TestRoles.ANONYMOUS,
    TestRoles.DEFAULT,
    TestRoles.SUPERADMIN,
    TestRoles.ORG_ADMIN,
    TestRoles.ORG_FACILITATOR,
    TestRoles.ORG_USER,
    TestRoles.ORG_VIEWER,
]

MODELS = [
    "organization",
    "people_group",
    "project",
    "project_tab",
    "user",
    "researcher",
    "document",
    "structure",
]


class ModulesCountTestCase(JwtAPITestCase):
    """
    The API test client skips the `modules` counts by default (see `JwtClient`),
    so this test runs every module of every model for each role, to make sure
    they can all be computed.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.organization = OrganizationFactory()
        project = ProjectFactory(organizations=[cls.organization])
        cls.instances = {
            "organization": cls.organization,
            "people_group": PeopleGroupFactory(organization=cls.organization),
            "project": project,
            "project_tab": ProjectTabFactory(project=project),
            "user": UserFactory(groups=[cls.organization.get_users()]),
            "researcher": ResearcherFactory(),
            "document": DocumentFactory(),
            "structure": StructureFactory(organization=cls.organization),
        }

    def test_all_models_with_modules_are_tested(self):
        self.assertSetEqual(
            {type(instance) for instance in self.instances.values()},
            set(_modules.keys()),
        )

    @parameterized.expand(
        [(model, role) for model in MODELS for role in ROLES],
    )
    def test_count_modules(self, model, role):
        instance = self.instances[model]
        user = self.get_parameterized_test_user(role, instances=[self.organization])
        user = user or AnonymousUser()
        expected_keys = set(instance.get_related_module().modules_keys())
        for organization in (self.organization, None):
            modules = instance.modules_by_user(user, organization=organization)
            counts = modules.count()
            self.assertSetEqual(set(counts.keys()), expected_keys)
            for name, count in counts.items():
                self.assertIsInstance(count, int, f"{model}.{name}")
