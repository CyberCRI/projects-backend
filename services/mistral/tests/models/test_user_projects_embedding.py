from faker import Faker

from apps.accounts.factories import UserFactory
from apps.commons.test import JwtAPITestCase
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory
from services.mistral.factories import (
    ProjectEmbeddingFactory,
    UserProjectsEmbeddingFactory,
)
from services.mistral.testcases import MistralTestCaseMixin

faker = Faker()


class ProjectEmbeddingVisibilityTestCase(JwtAPITestCase):
    def test_set_visibility_visible(self):
        project = ProjectFactory()
        ProjectEmbeddingFactory(item=project, is_visible=True, embedding=1024 * [1])
        user = UserFactory(groups=[project.get_members()])
        embedding = UserProjectsEmbeddingFactory(item=user)
        embedding.set_visibility()
        self.assertTrue(embedding.is_visible)

    def test_set_visibility_not_visible(self):
        user = UserFactory()
        embedding = UserProjectsEmbeddingFactory(item=user)
        embedding.set_visibility()
        self.assertFalse(embedding.is_visible)


class VectorizeUserProjectsTestCase(JwtAPITestCase, MistralTestCaseMixin):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()

        cls.project_1 = ProjectFactory(organizations=[cls.organization])
        cls.project_2 = ProjectFactory(organizations=[cls.organization])
        cls.vector_1 = [
            round(faker.pyfloat(min_value=0, max_value=1), 2) for _ in range(1024)
        ]
        cls.vector_2 = [
            round(faker.pyfloat(min_value=0, max_value=1), 2) for _ in range(1024)
        ]

        cls.embedding_1 = ProjectEmbeddingFactory(
            item=cls.project_1,
            is_visible=True,
            embedding=cls.vector_1,
        )
        cls.embedding_2 = ProjectEmbeddingFactory(
            item=cls.project_2,
            is_visible=True,
            embedding=cls.vector_2,
        )

    def test_vectorize_user_projects(self):
        user = UserFactory(groups=[self.project_1.get_members()])
        embedding = UserProjectsEmbeddingFactory(item=user)
        embedding.vectorize()
        self.assertTrue(embedding.is_visible)
        self.assertEqual(
            [round(e, 2) for e in embedding.embedding],
            [round(e, 2) for e in self.vector_1],
        )

    def test_vectorize_user_projects_multiple_projects(self):
        user = UserFactory(
            groups=[self.project_1.get_members(), self.project_2.get_owners()]
        )
        embedding = UserProjectsEmbeddingFactory(item=user)
        embedding.vectorize()
        average_vector = [
            (self.vector_1[i] + 2 * self.vector_2[i]) / 3 for i in range(1024)
        ]
        self.assertTrue(embedding.is_visible)
        self.assertEqual(
            [round(e, 2) for e in embedding.embedding],
            [round(e, 2) for e in average_vector],
        )
