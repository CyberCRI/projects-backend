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
        cls.project_3 = ProjectFactory(organizations=[cls.organization])

        cls.vector_1 = [
            round(faker.pyfloat(min_value=0, max_value=1), 2) for _ in range(1024)
        ]
        cls.vector_2 = [
            round(faker.pyfloat(min_value=0, max_value=1), 2) for _ in range(1024)
        ]
        cls.vector_3 = [
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
        cls.embedding_3 = ProjectEmbeddingFactory(
            item=cls.project_3,
            is_visible=True,
            embedding=cls.vector_3,
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
            groups=[
                self.project_1.get_members(),
                self.project_2.get_reviewers(),
                self.project_3.get_owners(),
            ]
        )
        embedding = UserProjectsEmbeddingFactory(item=user)
        embedding.vectorize()
        score_1 = self.project_1.get_or_create_score().score
        score_2 = self.project_2.get_or_create_score().score
        score_3 = self.project_3.get_or_create_score().score
        average_vector = [
            (
                score_1 * self.vector_1[i]
                + score_2 * self.vector_2[i]
                + 2 * score_3 * self.vector_3[i]
            )
            / (score_1 + score_2 + 2 * score_3)
            for i in range(1024)
        ]
        self.assertTrue(embedding.is_visible)
        self.assertEqual(
            [round(e, 2) for e in embedding.embedding],
            [round(e, 2) for e in average_vector],
        )
