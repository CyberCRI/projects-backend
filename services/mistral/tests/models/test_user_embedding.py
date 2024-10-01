from unittest.mock import patch

from faker import Faker

from apps.accounts.factories import UserFactory
from apps.commons.test import JwtAPITestCase
from apps.organizations.factories import OrganizationFactory
from apps.projects.factories import ProjectFactory
from apps.skills.factories import SkillFactory
from services.mistral.factories import ProjectEmbeddingFactory, UserEmbeddingFactory
from services.mistral.testcases import MistralTestCaseMixin

faker = Faker()


class UserEmbeddingVisibilityTestCase(JwtAPITestCase):
    def test_set_visibility_with_personal_description(self):
        user = UserFactory(
            personal_description=faker.text(), professional_description=""
        )
        embedding = UserEmbeddingFactory(item=user)
        embedding.set_visibility()
        self.assertTrue(embedding.is_visible)

    def test_set_visibility_with_professional_description(self):
        user = UserFactory(
            personal_description="", professional_description=faker.text()
        )
        embedding = UserEmbeddingFactory(item=user)
        embedding.set_visibility()
        self.assertTrue(embedding.is_visible)

    def test_set_visibility_with_skills(self):
        user = UserFactory(personal_description="", professional_description="")
        embedding = UserEmbeddingFactory(item=user)
        SkillFactory(user=user, level=3)
        embedding.set_visibility()
        self.assertTrue(embedding.is_visible)

    def test_set_visibility_with_project(self):
        project = ProjectFactory()
        ProjectEmbeddingFactory(item=project, is_visible=True, embedding=1024 * [1])
        user = UserFactory(
            personal_description="",
            professional_description="",
            groups=[project.get_members()],
        )
        embedding = UserEmbeddingFactory(item=user)
        embedding.set_visibility()
        self.assertTrue(embedding.is_visible)

    def test_set_visibility_not_visible(self):
        user = UserFactory(personal_description="", professional_description="")
        embedding = UserEmbeddingFactory(item=user)
        SkillFactory(user=user, level=2)
        embedding.set_visibility()
        self.assertFalse(embedding.is_visible)


class VectorizeUserTestCase(JwtAPITestCase, MistralTestCaseMixin):
    @classmethod
    def setUpTestData(cls) -> None:
        super().setUpTestData()
        cls.organization = OrganizationFactory()

    @patch("services.mistral.interface.MistralService.service.chat")
    @patch("services.mistral.interface.MistralService.service.embeddings")
    def test_user_embedding(self, mocked_embeddings, mocked_chat):
        project_1 = ProjectFactory(organizations=[self.organization])
        project_2 = ProjectFactory(organizations=[self.organization])
        projects_vector_1 = [
            round(faker.pyfloat(min_value=0, max_value=1), 2) for _ in range(1024)
        ]
        projects_vector_2 = [
            round(faker.pyfloat(min_value=0, max_value=1), 2) for _ in range(1024)
        ]
        ProjectEmbeddingFactory(
            item=project_1, is_visible=True, embedding=projects_vector_1
        )
        ProjectEmbeddingFactory(
            item=project_2, is_visible=True, embedding=projects_vector_2
        )
        profile_embedding = [
            round(faker.pyfloat(min_value=0, max_value=1), 2) for _ in range(1024)
        ]

        mocked_chat.return_value = self.chat_response_mocked_return(
            [faker.sentence() for _ in range(3)]
        )
        mocked_embeddings.return_value = self.embedding_response_mocked_return(
            profile_embedding
        )

        user = UserFactory(groups=[project_1.get_members(), project_2.get_members()])
        embedding = UserEmbeddingFactory(item=user)
        embedding.vectorize()

        user.refresh_from_db()
        project_1.refresh_from_db()
        project_2.refresh_from_db()

        self.assertIsNotNone(user.profile_embedding)
        self.assertIsNotNone(user.projects_embedding)

        self.assertIsNotNone(user.score)
        self.assertIsNotNone(project_1.score)
        self.assertIsNotNone(project_2.score)

        self.assertNotEqual(user.score, 0)
        self.assertNotEqual(project_1.score.score, 0)
        self.assertNotEqual(project_2.score.score, 0)

        self.assertIsNotNone(user.projects_embedding.embedding)
        self.assertIsNotNone(user.profile_embedding.embedding)

        self.assertNotEqual(user.profile_embedding.prompt_hashcode, "")

        profile_embedding = user.profile_embedding.embedding
        projects_embedding = user.projects_embedding.embedding
        profile_score = 2 * user.score.score
        projects_score = project_1.score.score + project_2.score.score

        expected_result = [
            round(
                (
                    profile_score * profile_embedding[i]
                    + projects_score * projects_embedding[i]
                )
                / (profile_score + projects_score),
                2,
            )
            for i in range(1024)
        ]
        self.assertEqual([round(e, 2) for e in embedding.embedding], expected_result)
